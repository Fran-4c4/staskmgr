import docker

import logging
from taskmgr.tmgr.task_handler_interface import TaskHandlerInterface

class DockerTaskHandler(TaskHandlerInterface):
    """Class to handle running Docker containers as tasks."""

    task_data=None

    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.task_data=None

        """Initialize DockerTaskRunner with the task definition.
        
        Args:
            task_definition (dict): The task definition that contains the Docker configuration.
        """
        self.image = None
        self.name = None
        self.environment = None
        self.volumes = None
        self.command = None
        self.client = docker.from_env()
        
    def config(self):
        """config class
        """ 
        self.image = self.task_data.get('image')
        self.name = self.task_data.get('name', None)
        self.environment = self.task_data.get('environment', {})
        self.volumes = self.task_data.get('volumes', {})
        self.command = self.task_data.get('command', None)
        self.client = docker.from_env()        

    def run_task(self, **kwargs):
        """Run the Docker container task."""
        try:
            task_definition=kwargs.get("task_definition")
            if task_definition is None:
                raise Exception ("ECSTaskHandler: Task definition is None. Please check definition data.")    
                
            self.task_data=task_definition
            
            self.config()
            print(f"Running Docker container with image: {self.image}")

            # Ejecutar el contenedor Docker
            container = self.client.containers.run(
                self.image,
                name=self.name,
                environment=self.environment,
                volumes=self.volumes,
                command=self.command,
                detach=True  # Detach mode, so the container runs in the background
            )
            
            print(f"Container {container.short_id} is running.")
            
            # Esperar a que el contenedor termine y obtener el log de salida
            result = container.wait()
            logs = container.logs().decode('utf-8')
            print(f"Container logs: {logs}")
            
            container.remove()  # Opcional: eliminar el contenedor después de la ejecución
            
            return {"status": "COMPLETED", "logs": logs, "exit_code": result['StatusCode']}
        
        except docker.errors.ContainerError as e:
            return {"status": "ERROR", "message": str(e)}
        except docker.errors.ImageNotFound as e:
            return {"status": "ERROR", "message": f"Image not found: {self.image}"}
        except Exception as e:
            return {"status": "ERROR", "message": str(e)}
