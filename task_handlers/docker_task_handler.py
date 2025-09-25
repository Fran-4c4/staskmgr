import os
import datetime
try:
    import docker
except ImportError:
    raise ImportError(
        "'docker' is not installed. Install using 'pip install docker'."
    )

import logging
from tmgr.task_handler_interface import TaskHandlerInterface
from docker.errors import ContainerError, ImageNotFound, DockerException
from dotenv import dotenv_values

class DockerTaskHandler(TaskHandlerInterface):
    """
    Handles execution of tasks as Docker containers.

    Attributes:
        log (logging.Logger): Logger instance for this handler.
        client (docker.DockerClient): Docker client initialized from environment.
        task_data (dict): Dictionary with task configuration parameters.
        id_task (any): id task to identifies the task 
        image (str): Docker image name for the container.
        name (str): Optional container name.
        environment (dict): Environment variables to pass to the container.
        volumes (dict): Volume mounts for the container.
        command (list or str): Command and arguments to run in container.
        entrypoint (list or str): Optional entrypoint override for container.
        networks (list): List of networks to connect the container to.
        restart_policy (str): Container restart policy (if used). Example:restart_policy = {"Name": "on-failure", "MaximumRetryCount": 5}
        environment_files (dict): Dict with host_path and container_path for env file mount.
        container_remove (bool): boolean to indicate if we need to close the container or not
    """

    def __init__(self):
        """
        Initializes DockerTaskHandler instance.

        Sets up logging and Docker client.
        Initializes configuration variables used for running the container.
        """
        self.log = logging.getLogger(__name__)          # Logger for debug/info/error messages
        self.client = docker.from_env()                 # Docker client connected to local Docker engine
        self.task_data:dict = None                      # Full task configuration dict from BBDD
        self.id_task:str=None                        # id task
        self.image:str = None                        # Docker image to run
        self.name:str = None                         # Optional name for the container instance
        self.environment:dict = None                  # Environment variables (dict) for container
        self.volumes:dict = None                      # Volume bindings as dict {host_path: {bind, mode}}
        self.command:str|list = None                  # Command and args to run inside container
        self.entrypoint = None                        # Entrypoint override for container, if any
        self.networks:list = None                     # List of network names to connect container to
        self.restart_policy = None                    # Restart policy restart_policy = {"Name": "on-failure", "MaximumRetryCount": 5}
        self.environment_files:dict = None            # Dict with host_path and container_path for env file
        self.container_remove:bool = None             #  boolean to indicate if we need to close the container or not
        self.wait_for_completion:bool = False         #  boolean to indicate if we want to wait for completion

    def config(self):
        """
        Configures task parameters from task_data.

        Ensures required Docker run parameters are extracted including
        image, container name, environment variables, volumes, command,
        entrypoint, networks, and environment_files mount path.
        """
        if not self.task_data:
            raise ValueError("task_data has not been assigned for configuration")
        
        self.id_task=str(self.task_data["task_id_task"])

        self.image = self.task_data.get('image')
        if not self.image:
            raise ValueError("Docker image ('image') is required in task_data")

        self.name = self.task_data.get('name', None)

        # Environment variables as dict
        self.environment = self.task_data.get('environment', {})

        self.volumes = self.task_data.get('volumes', {}).copy()
        
        # Read environment_files array 
        self.environment_files = self.task_data.get('environment_files', [])        
        for entry in self.environment_files:
            env_type: str = entry.get('type', "")
            if env_type.upper() == "LOCAL":
                host_path = entry.get('value')
                if host_path and os.path.isfile(host_path):
                    env_vars = dotenv_values(host_path)  # parse .env file into dictionary
                    if self.environment:
                        self.environment.update(env_vars)
                    else:
                        self.environment = env_vars
                else:
                    self.log.warning(f"Environment file not found or inaccessible: {host_path}")

        # Command to override entrypoint arguments           
        self.command=self._config_command()

        # Entrypoint list or string (optional)
        self.entrypoint = self.task_data.get('entrypoint', None)

        # Network(s) to connect container to; docker-py supports single network string
        # If multiple networks, connect manually after container start
        self.networks = self.task_data.get('networks', [])

        # Restart policy (not directly supported in run command, typically used in compose)
        self.restart_policy = self.task_data.get('restart_policy', None)
        
        self.container_remove       = self.task_data.get('container_remove', True)
        self.wait_for_completion    = self.task_data.get('wait_for_completion', False)

    def _config_command(self):
        """
        Configure the command to override entrypoint arguments by injecting the actual id_task.

        If 'command' in task_data contains a placeholder (<idtask>) or the flag '--idtask',
        replace or append the task id accordingly.

        Returns:
            The replaced or original 'command' (str or list), or None if no command defined.
        """
        command= self.task_data.get('command', None)
        if command is None: 
            return None
        if isinstance(command, str):
            if "<idtask>" in command:
                command = command.replace("<idtask>", self.id_task)
        elif isinstance(command, list):
            if "--idtask" in command:
                # find index and replace next value
                idx = command.index("--idtask")
                if idx + 1 < len(command):
                    command[idx+1] = self.id_task
                else:
                    command.append(self.id_task)

            
        return command
    
    @staticmethod
    def generate_container_name(id_task):
        prefix = "task"
        uuid_part = id_task.replace("-", "")[:8]  # primeros 8 hex sin guiones
        timestamp = datetime.datetime.now().strftime("%y%m%d%H%M%S")  # YYMMDDHHMMSS
    
        return f"{prefix}-{uuid_part}-{timestamp}"
    
    def run_task(self, **kwargs):
        """
        Executes the Docker container as an isolated task.

        Parameters expected in kwargs:
            - task_definition (dict): task configuration with Docker parameters.

        Returns:
            dict with status, logs, exit code or error message.
        """
        try:
            task_definition = kwargs.get("task_definition")
            if task_definition is None:
                raise Exception("DockerTaskHandler: task_definition is None, check configuration.")

            self.task_data = task_definition
            self.config()

            self.log.info(f"Launching Docker container with image: {self.image}")

            
            unique_name = self.generate_container_name(id_task=self.id_task)
            # Run container detached, to allow network attaching and waiting manually
            container = self.client.containers.run(
                image=self.image,
                name=unique_name, #we need a unique name if we use multiples containers
                environment=self.environment,
                volumes=self.volumes,
                command=self.command,
                entrypoint=self.entrypoint,
                detach=True,
                network=self.networks[0] if self.networks else None,  # attach first network initially
                remove=(self.container_remove if not self.wait_for_completion else False),  # manual removal to fetch logs etc
                restart_policy= self.restart_policy
            )

            # Attach to additional networks if specified more than one
            if len(self.networks) > 1:
                for net in self.networks[1:]:
                    try:
                        network = self.client.networks.get(net)
                        network.connect(container)
                    except docker.errors.NotFound:
                        self.log.error(f"Network not found: {net}")

            self.log.info(f"Container {container.short_id} started, waiting for completion...")

            if self.wait_for_completion:
                exit_status = container.wait()  # blocking wait for container to finish

                logs = container.logs().decode('utf-8')

                self.log.info(f"Container {container.short_id} finished with exit code {exit_status['StatusCode']}")
                self.log.debug(f"Container logs:\n{logs}")
                if self.container_remove:
                    container.remove()
                    self.log.info(f"Container {container.short_id} removed after execution")
                return {
                    "status": "COMPLETED",
                    "logs": logs,
                    "exit_code": exit_status['StatusCode']
                }

            else:
                self.log.info(f"Container {container.short_id} started asynchronously")
                return {
                    "status": "STARTED",
                    "container_id": container.short_id,
                    "exit_code": 0
                }
            
        except ContainerError as e:
            msg=f"Docker container error: {str(e)}"
            self.log.error(msg)
            raise Exception(msg)

        except ImageNotFound as e:
            msg=f"Docker image not found: {self.image}"
            self.log.error(msg)
            raise Exception(msg)

        except DockerException as e:
            msg=f"Docker general error: {str(e)}"
            self.log.error(msg)
            raise Exception(msg)


        except Exception as e:
            msg=f"Unexpected error in Docker task execution: {str(e)}"
            self.log.error(msg)
            raise Exception(msg)