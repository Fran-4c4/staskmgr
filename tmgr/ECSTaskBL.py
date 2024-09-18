from typing import Dict
import boto3
import json
import logging

class ECSTaskBL():
    
    
    client=None
    task_data=None

    def __init__(self, task_definition:Dict):
        self.log = logging.getLogger(__name__)
        self.client = None
        if task_definition is None:
            raise Exception ("ECSTaskBL: Task definition is None. Please check definition data.")    
            
        self.task_data=task_definition

        self.aws_region = self.task_data['region']
        self.aws_subnets = self.task_data['subnets']
        self.aws_security_groups = self.task_data['security_groups']
        self.aws_cluster_name = self.task_data['cluster_name']
        self.aws_task_definition = self.task_data['task_definition']
        self.aws_task_container_name = self.task_data['task_container_name']
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


    def launch_ai_task(self, aws_task_cmd:list)->bool: 
        """Launch a task in a ECS cluster for EC2 type

        Args:
            aws_task_cmd (list): Command list

        Returns:
            bool: Launch Result. True=Success | False=Failure
        """
        if self.client:
            response = self.client.run_task(
                taskDefinition=self.aws_task_definition,
                launchType=self.launchType,
                cluster=self.aws_cluster_name,
                count=1,
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
        

    def launch_task(self, aws_task_cmd:list)->bool: 
        """Launch a task in a ECS cluster for fargate type

        Args:
            aws_task_cmd (list): Command list

        Returns:
            bool: Launch Result. True=Success | False=Failure
        """
        if self.client:
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
    

