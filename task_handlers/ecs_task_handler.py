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
        response=None
        aws_task_cmd = []
        id_process=self.task_data.get("task_id_task",None)
        if id_process:
            aws_task_cmd = ['--idprocess', str(id_process)]
            
        asg_instances=self.check_ASG_capacity()
        if asg_instances==0:
            self.log.info("No Container Instances were found in your cluster, increasing ASG(Auto scaling group)...")
            self.increase_ASG_capacity()
            instance_ready=self.checkInstanceStatus()
            if not instance_ready:
                raise Exception(f"There is no instances ready to deploy task {id_process}.")
        else:
            self.log.debug(f"ASG has {asg_instances} instances")
            
            
        def run_task():
            try:
                response = self.client.run_task(
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
                return response      
            except Exception as e:                
                if "No Container Instances were found in your cluster" in str(e):
                    self.log.info("No Container Instances were found in your cluster...")
                    return None
                else:
                    raise e  
            
            
        while response is None and attempts < max_attempts:
            response = run_task()
            if response is None:
                attempts += 1
                self.log.info(f"Task was not deployed, waiting {self.auto_scaling_group_wait_time}seconds ... Try {attempts}/{max_attempts}")
                time.sleep(self.auto_scaling_group_wait_time)  # Esperar un tiempo antes de volver a intentar

        if response and 'failures' in response and len(response['failures']) == 0:
            log_resp=json.dumps(response, indent=4, default=str)
            self.log.info(f"Instance launched. {log_resp}")
            return True
        else:
            raise Exception(f"There is an error throwing the task. {str(response)}" )


    def checkInstanceStatus(self):
        """check instance status in ASG group

        Returns:
            boolean: true if there is an instance ready for deploying
        """        
        # Check ASG for 'InService' instance
        log=self.log
        instance_ready = False
        autoscaling_client = boto3.client('autoscaling', region_name=self.aws_region)
        ec2_client = boto3.client('ec2')
        attempts = 0
        max_attempts = self.task_data.get("max_attempts",10)
        while not instance_ready and attempts < max_attempts:
            attempts += 1
            response = autoscaling_client.describe_auto_scaling_instances()
            instance_id = None

            for instance in response['AutoScalingInstances']:
                if instance['AutoScalingGroupName'] == self.auto_scaling_group_name and instance['LifecycleState'] == 'InService':
                    instance_id = instance['InstanceId']
                    log.debug(f"Instance {instance_id} is in 'InService' state.")
                    break

            if instance_id:
                # 3. Check instance status checks
                while True:
                    status_response = ec2_client.describe_instance_status(InstanceIds=[instance_id])
                    if status_response['InstanceStatuses']:
                        instance_status = status_response['InstanceStatuses'][0]
                        if (instance_status['InstanceStatus']['Status'] == 'ok' and
                                instance_status['SystemStatus']['Status'] == 'ok'):
                            log.debug(f"Instance {instance_id} has passed all status checks.")
                            instance_ready = True
                            break
                    log.debug(f"Waiting for instance {instance_id} to pass status checks...")
                    time.sleep(self.auto_scaling_group_wait_time)
            else:
                log.debug("Waiting for an 'InService' instance in ASG...")
                time.sleep(self.auto_scaling_group_wait_time)
                
        return instance_ready
        
    def increase_ASG_capacity(self):
        """increase Autoscaling group capacity
        """        
        autoscaling_client = boto3.client('autoscaling', region_name=self.aws_region)

        autoscaling_client.set_desired_capacity(
            AutoScalingGroupName=self.auto_scaling_group_name,
            DesiredCapacity=self.auto_scaling_group_DesiredCapacity,
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
    

