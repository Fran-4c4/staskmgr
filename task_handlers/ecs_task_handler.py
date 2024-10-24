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
        
        self.client = boto3.client("ecs", region_name=self.aws_region)

        self.platformVersion = None
        self.networkConfiguration = None
        
        if self.launchType == 'FARGATE':
            self.platformVersion = 'LATEST'

        if self.networkMode == 'awsvpc':
            self.networkConfiguration={
                    'awsvpcConfiguration': {
                        'subnets': self.aws_subnets,
                        'securityGroups': self.aws_security_groups,
                        'assignPublicIp': 'ENABLED'
                    }
                }

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
        if self.client:
            attempts = 0
            max_attempts = 10
            response=None
            aws_task_cmd = []
            id_process=self.task_data.get("task_id_task",None)
            if id_process:
                aws_task_cmd = ['--idprocess', str(id_process)]
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
                    autoscaling_client = boto3.client('autoscaling', region_name=self.aws_region)
                    if "No Container Instances were found in your cluster" in str(e):
                        self.log.info("No Container Instances were found in your cluster, increasing ASG(Auto scaling group)...")
                        autoscaling_client.set_desired_capacity(
                            AutoScalingGroupName=self.auto_scaling_group_name,
                            DesiredCapacity=self.auto_scaling_group_DesiredCapacity,
                            HonorCooldown=False
                        )
                        return None
                    else:
                        raise e  
                
                
            while response is None and attempts < max_attempts:
                response = run_task()
                if response is None:
                    attempts += 1
                    self.log.info(f"Increasing autoscaling group, waiting {self.auto_scaling_group_wait_time}seconds ... Try {attempts}/{max_attempts}")
                    time.sleep(self.auto_scaling_group_wait_time)  # Esperar un tiempo antes de volver a intentar
        

            
            
            if response and 'failures' in response and len(response['failures']) == 0:
                log_resp=json.dumps(response, indent=4, default=str)
                self.log.info(f"Instance launched. {log_resp}")
                return True
            else:
                raise Exception(f"There is an error throwing the task. {str(response)}" )
        else:
            raise Exception("There is an error throwing the task. Task client is not loaded ")
        
        
        

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
    

