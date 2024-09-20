
import logging
import logging.handlers
import time
from typing import Dict

from .periodic_task import PeriodicTask

from .global_config import gconfig
from .db_mgr import DBMgr
from .configuration_helper import ConfigurationHelper
from .db_base import DBBase
from .task_db import TaskDB
from .enums.task_status_enum import TaskStatusEnum
from .task_loader import TaskLoader
class TMgr():
    """class to manage task from DDBB

    Returns:
        int: value of the task
    """    
    configuration_file=None #"appconfig.json"
    
    task_definitions={}
    
    th_check_configuration=None
    
    def __init__(self,config_like:any,taskmgr_name="staskmgr"):
        """
        Initializes TaskManager.

        Args:
            config_like (any): dict configuration or file path to load configuration
            taskmgr_name (str, optional): Name of the task manager. This is the key name in DDBB configuration. Default to "staskmgr".

        Attributes:
            configuration_file (any): Store the file name of the configuration, not used yet but in future it can be reloaded automatically to retrieve new configuration.
            log (logging.Logger): application logs            
            wait_between_tasks_seconds (int): Wait time between checking task to avoid query DDBB all the time. When Redis or similar will be used this must be changed.
            monitor_wait_time_seconds (int): Wait time before close task manager. 
            max_wait_count (int): max wait time. This is useful when you create a manager in a docker and you want to wait to reutilize the hardware. Task manager will wait this time by the number of counts.
        """
        self.log = logging.getLogger(__name__)
        self.configuration_file=config_like  
        self.max_wait_count=10
        self.wait_between_tasks_seconds=1
        self.monitor_wait_time_seconds=-1

        self.init_configuration(config_like=config_like)
        

        
    @property
    def app_config(self):
        """get global configuration

        Returns:
            dict: global configuration
        """        
        return gconfig.app_config

    @app_config.setter
    def app_config(self, value):
        """set global configuration

        Args:
            value (dict): global configuration
        """        
        gconfig.app_config = value

    def init_configuration(self,config_like:any):
        """init configuration

        Args:
            config_like (str|dict): a dict with configuration or a file with configuration
        """        
        cfgh=ConfigurationHelper() 
        self.app_config= cfgh.load_config(config_like= config_like)  
        #INIT DATABASE
        db_config=self.app_config["DDBB_CONFIG"]
        DBMgr().init_database(db_config)

        self.config_tmgr_from_ddbb() 
        self.log.info("Initial DDBB configuration loaded.")       
        self.config_task_definitions()
        
        if self.app_config.get("check_configuration_interval",-1)>0:
            self.th_check_configuration=PeriodicTask(interval=10, task_function=self.config_tmgr_from_ddbb)
            self.th_check_configuration.start()
        
    def config_tmgr_from_ddbb(self):
        """config manager

        Args:
            cfg (dict): dict with configuration
        """        
        cfg:Dict=TaskDB().get_task_mgr_configuration(self.app_config["manager_name"]).config
        self.app_config["mgr_config"]=cfg
        self.max_wait_count=cfg.get("max_wait_count",10) 
        self.wait_between_tasks_seconds=cfg.get("wait_between_tasks_seconds",1) 
        self.monitor_wait_time_seconds=cfg.get("monitor_wait_time_seconds",-1) 
        self.log.debug("Configuration loaded...................................")
        
        
    def config_task_definitions(self): 
        """Configure task handlers
        """           
        self.task_definitions=self.app_config.get("task_handlers",{})

    def stop_tasks(self):
        """stop internal threads
        """        
        self.log.info("Stop threads")
        if self.th_check_configuration:
            self.th_check_configuration.stop()
          
    def get_task(self, id_task) :
        """return task object

        Args:
            id_task (uuid|str): id of the task

        Returns:
            Task: Task
        """        
        task=TaskDB().get_task(id_task)
        return task
            
    def fetch_pending_tasks(self):
        """return 1 pending task

        Returns:
            Any: task row
        """        
        db=DBBase()
        session = db.getsession()
        try:
            task_types=self.app_config["mgr_config"].get("config",{}).get("task_types")
            task=TaskDB(scoped_session=session).get_pending_task(task_types=task_types) 
            return task
        except Exception as oEx:
            raise 
        finally:
            db.closeSession()
            
    def task_definition(self,task_definition):
        """return task definition

        Returns:
            Any: task definition row
        """        
        db=DBBase()
        session = db.getsession()
        try:
            task=TaskDB(scoped_session=session).get_task_definition(task_type=task_definition) 
            if task:
                return task.config
            else:
                #find in configured files
                task=self.task_definitions[task_definition]
                if task is None:
                    raise Exception(f"Task definition not found {task_definition}")
                else:
                    return task
        except Exception as oex:
            raise 
        finally:
            db.closeSession()            
    
    def execute_task(self,id_task):
        """launch a task based on the task info

        Args:
            id_task (uuid|str): id of the task

        Returns:
            _type_: _description_
        """      
        log=self.log
        log.info(f"Executing task...{id_task}")   
        task_ret=0
        db=DBBase()
        session=db.getsession()
        proc_db=TaskDB(scoped_session=session)

        try:
           
            #update task to WAIT_EXECUTION
            resp=proc_db.update_status(id=id_task,new_status=TaskStatusEnum.CHECKING,prev_status=TaskStatusEnum.PENDING )
            if resp["status"]==TaskStatusEnum.CHECKING:   
                #hasta que cambiemos el proceso en fargate
                # proc_db.update_status(id=id_task,new_status=TaskStatusEnum.PENDING,prev_status=TaskStatusEnum.CHECKING) 
                launchType=None  
                task_obj=self.get_task(id_task)
                task_type=str(task_obj.type).upper()  
                task_ret={} #self.tasks_list[task_type](**_params)
                task_config=self.task_definition(task_definition=task_type)                
                if task_config is None:
                    msg=f"task definition not recognized: {task_type}"
                    proc_db.update_status(id=id_task,new_status=TaskStatusEnum.ERROR,output=msg)
                    return 

                
                launchType=task_config["task_handler"].get("launchType","")
                if not "task_definition" in task_config:
                    task_config["task_definition"]={}
                task_config["task_definition"]["task_id_task"]=str(id_task)
                resp=proc_db.update_status(id=id_task,new_status=TaskStatusEnum.WAIT_EXECUTION )
                tl=None
                try:
                    tl=TaskLoader(task_config)
                    #-----------START TASK  --------------------
                    
                    task_ret=tl.run_task()
                    
                    #-----------END TASK    --------------------
                except Exception as ex:
                    # here we manage errors inside class, not logical or functional errors that are controlled in task_ret var.
                    msg=str(ex)
                    proc_db.update_status(id=id_task,new_status=TaskStatusEnum.ERROR,output=msg,progress=0) 

                if task_ret.get("status","").upper()=="ERROR":
                    msg=task_ret['message']
                    proc_db.update_status(id=id_task,new_status=TaskStatusEnum.ERROR,output=msg) 
                    log.error(f"Task {id_task} launched with errors: {msg}") 
                else:
                    if launchType=="INTERNAL": 
                        msg=task_ret.get('message',None)
                        progress=100
                        proc_db.update_status(id=id_task,new_status=TaskStatusEnum.FINISHED,output=msg,progress=progress) 
                    log.info(f"Task {id_task} launched sucessfully.")       
            else:
                # No se ha podido actualizar, bien porque se ha borrado, porque ya se ha ejecutado, etc. 
                log.warning(f"Task {id_task} not launched. Maybe was deleted or executed in other process.")  

        except Exception as ex:
            self.log.error(f"Task {id_task} raised error {str(ex)}")


    
    def monitor_and_execute(self):
        """check and execute pending tasks
        """                
        try:
            max_wait_counter=0
            while True:
                task = self.fetch_pending_tasks()
                if task:
                    task_id = str(task.id)
                    self.execute_task(task_id)  
                    next_task_wait_seconds=task.config.get("next_task_wait",0)
                    if self.wait_between_tasks_seconds >0 or next_task_wait_seconds>0: 
                        #When we use this? When the task is executed in a thread, or in flow where we want to wait a time like upscalling resources 
                        if next_task_wait_seconds>  self.wait_between_tasks_seconds:
                           wait_between_tasks_seconds= next_task_wait_seconds
                        else:
                           wait_between_tasks_seconds =self.wait_between_tasks_seconds
                        time.sleep(wait_between_tasks_seconds) 
                    max_wait_counter=0                     
                else:                    
                    max_wait_counter+=1
                    if self.monitor_wait_time_seconds>0 and max_wait_counter==self.max_wait_count:
                        self.log.info(f"No pending tasks stopping Task manager. Wait time was {str(self.monitor_wait_time_seconds)} seconds ")
                        return
                if  self.monitor_wait_time_seconds>0:   
                    time.sleep(self.monitor_wait_time_seconds)  # Espera antes de volver a verificar
        finally:
            self.stop_tasks()
    
    






