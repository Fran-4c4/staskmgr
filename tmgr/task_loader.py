import importlib
import logging
import os
import sys

class TaskLoader:
    """Class to load modules dinamically

    """    
    
    
    config = None
    
    def __init__(self, config):
        """init TaskLoader

        Args:
            config (dict): loader configuration
        """        
        self.log = logging.getLogger(__name__)
        self.config = config
        self.task_info = self.config['task_handler']
        
        self.module_name = self.task_info['module']
        self.class_name = self.task_info['class']
        self.task_name = self.task_info['name']
        self.task_path = self.task_info.get('path')
        self._configure_task_path()
        
        
    def _configure_task_path(self):
        self.task_path = self.task_info.get('path')
        if self.task_path:
            task_path = self.task_path                   
            # Check if the path is absolute
            if not os.path.isabs(task_path):
                # If it's not absolute, resolve it relative to the application path
                app_path =sys.path[0] #os.path.dirname(os.path.abspath(__file__))  # Application's base directory
                task_path = os.path.abspath(os.path.join(app_path, task_path))  # Resolve the relative path
                self.log.debug(f"TaskLoader.configure_task_path {task_path}")

            # Check if the path exists and add to sys.path if it's not already there
            if os.path.exists(task_path) and task_path not in sys.path:
                sys.path.append(task_path)
            else:
                # Check if it's the default 'task_handlers' path
                if "task_handlers" == task_path:
                    curDir = os.path.dirname(os.path.abspath(__file__))
                    task_default_path = os.path.join(curDir, '..', 'config', "task_handlers")
                    if task_default_path not in sys.path:
                        sys.path.append(task_default_path)
        

    def run_task(self):
        """Perform task operation in dinamically class

        Args:
            **kwargs: Parameters to pass when calling `run_task`.

        Raises:
            ImportError: If the module cannot be loaded.
            AttributeError: If the class or method is missing.
            TypeError: If the class doesn't implement `run_task`.
        """
        
        task_ret={"status":"RUNNING"}        
        module_name = self.module_name
        class_name = self.class_name

        # Load module
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            msg=f"Error loading module: {module_name}. Details: {str(e)}"
            task_ret['status']="ERROR"
            task_ret['message']=msg
            task_ret['error_type']="ImportError"
            return task_ret

        # get class inside module
        try:
            task_class = getattr(module, class_name)
        except AttributeError as e:
            msg=f"Class '{class_name}' not found in module '{module_name}'. Details: {str(e)}"
            task_ret['status']="ERROR"
            task_ret['message']=msg
            task_ret['error_type']="AttributeError"
            return task_ret

        
        # Instance class
        try:
            task_instance = task_class()
        except TypeError as e:
            msg=f"Error instantiating class '{class_name}' details: {str(e)}"
            task_ret['status']="ERROR"
            task_ret['message']=msg
            task_ret['error_type']="TypeError"
            return task_ret            
        

        if not hasattr(task_instance, 'run_task'):
            msg=f"Class '{class_name}' must implement 'run_task'."
            task_ret['status']="ERROR"
            task_ret['message']=msg
            task_ret['error_type']="TypeError"
            return task_ret   
        
        try:
            task_params= {"task_definition": self.config.get('task_definition',None)}
            task_ret= task_instance.run_task(**task_params)
        except Exception as e:
            msg=f"Error executing 'run_task' in class '{class_name}': {str(e)}"
            task_ret['status']="ERROR"
            task_ret['message']=msg
            task_ret['error_type']="RuntimeError"
            return task_ret       
        
        return task_ret     
