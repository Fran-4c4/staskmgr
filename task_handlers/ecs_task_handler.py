import boto3
import json
import logging
import time

from tmgr.task_handler_interface import TaskHandlerInterface
from tmgr.task_correlation import (
    build_ecs_environment_overrides,
    build_ecs_tags,
    build_task_context,
)

class ECSTaskHandler(TaskHandlerInterface):
    """Launch tmgr tasks as ECS/Fargate or ECS/EC2 tasks."""

    client=None
    task_data=None

    def __init__(self):
        """Create an ECS task handler with empty AWS runtime state."""

        self.log = logging.getLogger(__name__)
        logging.getLogger('botocore').setLevel(logging.INFO)
        self.client = None
        self.task_data=None
        self.launchType = None
        self.networkMode = None
        self.task_context = {}
        self.ecs_environment_overrides = []
        self.ecs_tags = []
        self.auto_scaling_group_wait_time=60
        logging.getLogger('boto3').setLevel(level=logging.ERROR) #Set matplotlib log to CRITICAL level.

    def config(self):
        """Load ECS launch configuration and optional task metadata."""
               
        self.aws_region = self.task_data['region']
        self.aws_subnets = self.task_data['subnets']        
        self.aws_security_groups = self.task_data['security_groups']
        self.aws_cluster_name = self.task_data['cluster_name']
        self.aws_task_definition = self.task_data['task_definition']
        self.aws_task_container_name = self.task_data['task_container_name']
             
        # for autoscaling group
        self.auto_scaling_group_name=self.task_data.get('auto_scaling_group_name')
        self.auto_scaling_group_wait_time=self.task_data.get('auto_scaling_group_wait_time',60)
        self.auto_scaling_group_DesiredCapacity=self.task_data.get('auto_scaling_group_DesiredCapacity',1)
        
        self.launchType = self.task_data['launchType']
        self.networkMode = self.task_data['networkMode']
        
        self.platformVersion = self.task_data.get('platformVersion','LATEST')
        self.networkConfiguration = None
        self.task_context = build_task_context(task_definition=self.task_data)
        self.ecs_environment_overrides = build_ecs_environment_overrides(self.task_context)
        self.ecs_tags = build_ecs_tags(self.task_context)
        

        if self.networkMode == 'awsvpc':
            self.networkConfiguration={
                    'awsvpcConfiguration': {
                        'subnets': self.aws_subnets,
                        'securityGroups': self.aws_security_groups,
                        'assignPublicIp': 'ENABLED'
                    }
                }        
        
        self.client = boto3.client("ecs", region_name=self.aws_region)

    def _build_task_command(self):
        """Build the container command override with the current task id."""

        configured_command = self.task_data.get("command")
        id_process = self.task_data.get("task_id_task", None)
        if isinstance(configured_command, list):
            command = [str(item) for item in configured_command]
            for flag in ("--task-id", "--idtask", "--idprocess"):
                if flag in command and id_process:
                    index = command.index(flag)
                    if index + 1 < len(command):
                        command[index + 1] = str(id_process)
                    else:
                        command.append(str(id_process))
                    return command
            return [item.replace("<idtask>", str(id_process)) for item in command]
        if isinstance(configured_command, str):
            return [configured_command.replace("<idtask>", str(id_process))]
        if id_process:
            return ['--idprocess', str(id_process)]
        return []

    def _build_container_override(self, aws_task_cmd):
        """Build one ECS container override including optional metadata env."""

        container_override = {
            'name': self.aws_task_container_name,
            'command': aws_task_cmd
        }
        if self.ecs_environment_overrides:
            container_override["environment"] = self.ecs_environment_overrides
        return container_override

    def _build_success_response(self, response, mode):
        """Normalize an ECS run_task response into the handler contract."""

        tasks = response.get("tasks") or []
        task_arn = tasks[0].get("taskArn") if tasks else None
        return {
            "status": "STARTED",
            "message": f"ECS {mode} task launched.",
            "external_ref": task_arn,
            "task_arn": task_arn,
        }

    def run_task(self, **kwargs)->dict:
        """Launch one task in the configured ECS mode.

        Args:
            **kwargs: Expected to include `task_definition` with ECS launch
                metadata.

        Returns:
            dict: Launch result with `status` and optional `external_ref`.
        """     
        task_definition=kwargs.get("task_definition")
        if task_definition is None:
            raise Exception ("ECSTaskHandler: Task definition is None. Please check definition data.")    
            
        self.task_data=task_definition
        
        self.config()
        if self.launchType == 'FARGATE':
            return self.run_fargate_task()
        elif self.launchType == 'EC2':
            return self.run_ec2_task()            
        

    def run_ec2_task(self, **kwargs)->dict:
        """Launch a task in an EC2-backed ECS cluster.

        Returns:
            dict: Launch result with ECS task metadata.
        """
        if self.client is None:
            raise Exception("There is an error throwing the task. Boto3 Task client is none.")
  
        
        attempts = 0
        max_attempts = self.task_data.get("max_attempts",10)
        run_task_response=None
        id_process=self.task_data.get("task_id_task",None)
        aws_task_cmd = self._build_task_command()
            
        asg_capacity=self.check_ASG_capacity()
        if asg_capacity==0:
            self.log.info("No Container Instances were found in your cluster, increasing ASG(Auto scaling group)...")
            self.increase_ASG_capacity(self.auto_scaling_group_DesiredCapacity)
            instance_ready=self.checkInstanceStatus()
            if not instance_ready:
                raise Exception(f"There is no instances ready to deploy task {id_process}.")
        else:
            self.log.info(f"ASG has {asg_capacity} instances. Increasing + 1")
            self.increase_ASG_capacity(asg_capacity+1)
            instance_ready=self.checkInstanceStatus()
            if not instance_ready:
                raise Exception(f"There is no instances ready to deploy task {id_process}.")
            
        # even the instance is ready we need to wait to allocate the task
        run_task_response=None    
        while attempts < max_attempts:
            run_task_response = self.run_ecs_task(aws_task_cmd)
            if run_task_response in ["NO_CONTAINER_INSTANCES","NO_GPU"]:
                attempts += 1
                self.log.error(f"Task was not deployed, waiting {self.auto_scaling_group_wait_time}seconds ... Try {attempts}/{max_attempts}")
                time.sleep(self.auto_scaling_group_wait_time)  # Esperar un tiempo antes de volver a intentar

            elif run_task_response and 'failures' in run_task_response and len(run_task_response['failures']) == 0:
                log_resp=json.dumps(run_task_response, indent=4, default=str)
                self.log.info(f"Instance launched. {log_resp}")
                return self._build_success_response(run_task_response, "EC2")

                
        # if we get here we have an error stating the task
        raise Exception(f"There is an error throwing the task. {str(run_task_response)}" )


    def run_ecs_task(self,aws_task_cmd):
        try:
            run_task_response = self.client.run_task(
                taskDefinition=self.aws_task_definition,
                launchType=self.launchType,
                cluster=self.aws_cluster_name,
                overrides={
                    'containerOverrides': [
                        self._build_container_override(aws_task_cmd),
                    ]
                },
                **({"tags": self.ecs_tags} if self.ecs_tags else {})
            )        
            
            if run_task_response and 'failures' in run_task_response and len(run_task_response['failures']) == 0:
                log_resp=json.dumps(run_task_response, indent=4, default=str)
                self.log.info(f"Instance launched. {log_resp}")
                return run_task_response
            elif run_task_response and 'failures' in run_task_response and len(run_task_response['failures']) > 0:
                msg=str(run_task_response)
                if "No Container Instances were found in your cluster" in msg:
                    self.log.info(f"No Container Instances were found in your cluster={self.aws_cluster_name}")
                    return "NO_CONTAINER_INSTANCES"
                elif '"reason": "RESOURCE:GPU"' in msg:
                    self.log.error("No Container Instances with GPU...")
                    return "NO_GPU"            
                
            return run_task_response      
        except Exception as e:                
            if "No Container Instances were found in your cluster" in str(e):
                self.log.info("No Container Instances were found in your cluster...")
                return "NO_CONTAINER_INSTANCES"
            elif '"reason": "RESOURCE:GPU"' in str(e):
                self.log.error("No Container Instances with GPU...")
                return "NO_GPU"            
            else:
                raise e  


    def checkInstanceStatus(self):
        """Check the most recently launched instance status in ASG group.

        Returns:
            boolean: true if the most recent instance is ready for deploying
        """        
        log = self.log
        instance_ready = False
        autoscaling_client = boto3.client('autoscaling', region_name=self.aws_region)
        ec2_client = boto3.client('ec2')
        attempts = 0
        max_attempts = 30 #self.task_data.get("max_attempts", 10)

        while not instance_ready and attempts < max_attempts:
            attempts += 1

            # Get instance IDs for instances in the ASG that are in the 'InService' state
            response = autoscaling_client.describe_auto_scaling_instances()
            in_service_instance_ids = [
                instance['InstanceId'] for instance in response['AutoScalingInstances']
                if instance['AutoScalingGroupName'] == self.auto_scaling_group_name
                and instance['LifecycleState'] == 'InService'
            ]

            if in_service_instance_ids:
                # Get detailed information for each instance, including 'LaunchTime'
                instance_details = ec2_client.describe_instances(InstanceIds=in_service_instance_ids)
                instances_with_launch_time = [
                    {
                        'InstanceId': i['InstanceId'],
                        'LaunchTime': i['LaunchTime']
                    }
                    for reservation in instance_details['Reservations']
                    for i in reservation['Instances']
                ]

                # Sort by LaunchTime to get the most recent instance
                latest_instance = sorted(instances_with_launch_time, key=lambda x: x['LaunchTime'], reverse=True)[0]
                instance_id = latest_instance['InstanceId']
                log.debug(f"Checking status for the most recent instance: {instance_id}")
                attempts=0 #reset to filter here
                max_attempts = self.task_data.get("max_attempts", 10)
                # Check the status of the most recent instance
                while attempts < max_attempts:
                    attempts += 1
                    status_response = ec2_client.describe_instance_status(InstanceIds=[instance_id])
                    if status_response['InstanceStatuses']:
                        instance_status = status_response['InstanceStatuses'][0]
                        if (instance_status['InstanceStatus']['Status'] == 'ok' and
                                instance_status['SystemStatus']['Status'] == 'ok'):
                            log.info(f"Instance {instance_id} has passed all status checks.")
                            instance_ready = True
                            return instance_ready                        
                    log.debug(f"Waiting for instance {instance_id} to pass status checks...")
                    time.sleep(self.auto_scaling_group_wait_time)
            else:
                log.debug("Waiting for an 'InService' instance in ASG...")
                time.sleep(10)

        return instance_ready

        
    def increase_ASG_capacity(self,desired_capacity):
        """increase Autoscaling group capacity
        """        
        autoscaling_client = boto3.client('autoscaling', region_name=self.aws_region)

        autoscaling_client.set_desired_capacity(
            AutoScalingGroupName=self.auto_scaling_group_name,
            DesiredCapacity=desired_capacity,
            HonorCooldown=False
        )        
        
        
    def check_ASG_capacity(self):
        """check ASG capacity

        Returns:
            integer: number of instances running
        """        
        autoscaling_client = boto3.client('autoscaling', region_name=self.aws_region)
        
        response = autoscaling_client.describe_auto_scaling_groups(
            AutoScalingGroupNames=[self.auto_scaling_group_name]
        )
        self.log.debug("ASG info:"+ str(response))
        capacity=response['AutoScalingGroups'][0]['DesiredCapacity']
        if  capacity> 0:
            print(f"Auto scaling group {self.auto_scaling_group_name} has at least one instance running.")
        else:
            print(f"Auto scaling group {self.auto_scaling_group_name} has no instances running.")
            
        return capacity
        

    def run_fargate_task(self, **kwargs)->dict:
        """Launch a task in a Fargate-backed ECS cluster.

        Returns:
            dict: Launch result with ECS task metadata.
        """

        if self.client:
            aws_task_cmd = self._build_task_command()
               
            
            response = self.client.run_task(
                taskDefinition=self.aws_task_definition,
                launchType=self.launchType,
                cluster=self.aws_cluster_name,
                platformVersion=self.platformVersion,
                count=1,
                networkConfiguration=self.networkConfiguration,
                overrides={
                    'containerOverrides': [
                        self._build_container_override(aws_task_cmd),
                    ]
                },
                **({"tags": self.ecs_tags} if self.ecs_tags else {})
            )
            
            self.log.info(json.dumps(response, indent=4, default=str))
            if response and 'failures' in response and len(response['failures']) == 0:
                return self._build_success_response(response, "FARGATE")
            else:
                raise Exception("There is an error throwing the task")
        else:
            raise Exception("There is an error throwing the task. Task client is not loaded ")
    

