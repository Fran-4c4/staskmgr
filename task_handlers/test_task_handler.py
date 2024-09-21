
import logging

from tmgr.task_handler_interface import TaskHandlerInterface

class TestTaskHandler(TaskHandlerInterface):
    """sample task handler
    """     
    
    task_data=None
    
    def __init__(self, **kwargs):
        self.log = logging.getLogger(__name__)
        self.task_data=None

    
    def config(self):
        """config class
        """ 
        self.log.info(f"Config  test task with params: {self.task_data}")
        pass
    
       
    def run_task(self, **kwargs):
        task_definition=kwargs.get("task_definition")
        if task_definition is None:
            self.log.error("Task definition is None. Please check definition data.")
            raise Exception ("Task definition is None. Please check definition data.") 
        else:   
            self.log.info(f"Executing test task with task_definition: {task_definition}")
            
        self.task_data=task_definition
        self.config() #or we can pass the data here
        self.log.info(f"Executing test task with params: {kwargs}")
        