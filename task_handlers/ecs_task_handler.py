from typing import Dict
import boto3
import json
import logging
import time

from tmgr.task_handler_interface import TaskHandlerInterface

class ECSTaskHandler(TaskHandlerInterface):
    """handles ECS task. Can start a fargate task or an EC2 task


    """    
    client=None
    task_data=None

    def __init__(self):
        self.log = logging.getLogger(__name__)
        logging.getLogger('botocore').setLevel(logging.INFO)
        self.client = None
        self.task_data=None
        self.launchType = None
        self.networkMode = None
        self.auto_scaling_group_wait_time=60
        logging.getLogger('boto3').setLevel(level=logging.ERROR) #Set matplotlib log to CRITICAL level.

    def config(self):
        """config class
        """ 
               
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
        

        if self.networkMode == 'awsvpc':
            self.networkConfiguration={
                    'awsvpcConfiguration': {
                        'subnets': self.aws_subnets,
                        'securityGroups': self.aws_security_groups,
                        'assignPublicIp': 'ENABLED'
                    }
                }        
        
        self.client = boto3.client("ecs", region_name=self.aws_region)



    def run_task(self, **kwargs)->bool: 
        """Launch a task in a ECS cluster for fargate type

        Args:
            aws_task_cmd (list): Command list

        Returns:
            bool: Launch Result. True=Success | False=Failure
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
        

    def run_ec2_task(self, **kwargs)->bool: 
        """Launch a task in a ECS cluster for EC2 type

        Args:
            aws_task_cmd (list): Command list

        Returns:
            bool: Launch Result. True=Success | False=Failure
        """
        if self.client is None:
            raise Exception("There is an error throwing the task. Boto3 Task client is none.")
  
        
        attempts = 0
        max_attempts = self.task_data.get("max_attempts",10)
        run_task_response=None
        aws_task_cmd = []
        id_process=self.task_data.get("task_id_task",None)
        if id_process:
            aws_task_cmd = ['--idprocess', str(id_process)]
            
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
                return True

                
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
                        {
                            'name': self.aws_task_container_name,
                            'command': aws_task_cmd
                        },
                    ]
                }
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
        

    def run_fargate_task(self, **kwargs)->bool: 
        """Launch a task in a ECS cluster for fargate type

        Args:
            aws_task_cmd (list): Command list

        Returns:
            bool: Launch Result. True=Success | False=Failure
        """

        if self.client:
            aws_task_cmd = []
            id_process=self.task_data.get("task_id_task",None)
            if id_process:
                aws_task_cmd = ['--idprocess', str(id_process)]
               
            
            response = self.client.run_task(
                taskDefinition=self.aws_task_definition,
                launchType=self.launchType,
                cluster=self.aws_cluster_name,
                platformVersion=self.platformVersion,
                count=1,
                networkConfiguration=self.networkConfiguration,
                overrides={
                    'containerOverrides': [
                        {
                            'name': self.aws_task_container_name,
                            'command': aws_task_cmd
                        },
                    ]
                }
            )
            
            self.log.info(json.dumps(response, indent=4, default=str))
            if response and 'failures' in response and len(response['failures']) == 0:
                return True
            else:
                raise Exception("There is an error throwing the task")
        else:
            raise Exception("There is an error throwing the task. Task client is not loaded ")
    

