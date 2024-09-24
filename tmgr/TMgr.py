from re import search
import sys
import os
import json
import logging
import logging.handlers
import threading
import time
import argparse
from typing import Dict

from tmgr.model.config import Config

from .enums.lit_enum import LitEnum
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
    tasks_active=[]
    lock = threading.Lock()
    
    
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
        self.log.info(f"Starting STMR for {taskmgr_name}")  
        self.cfg=Config()
        self.cfg.taskmgr_name=taskmgr_name
        self.configuration_file=config_like  
        self.max_wait_counter=0
 
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
        
    @property
    def mgr_config(self):
        """get manager configuration

        Returns:
            dict: manager configuration
        """        
        return gconfig.app_config.get("mgr_config")    

    def init_configuration(self,config_like:any):
        """init configuration

        Args:
            config_like (str|dict): a dict with configuration or a file with configuration
        """        
        cfgh=ConfigurationHelper() 
        self.app_config= cfgh.load_config(config_like= config_like)  
        self.cfg.load_parse_cfg_file(config_like=self.app_config)
        #INIT DATABASE
        DBMgr().init_database(self.cfg.DDBB_CONFIG)
        self.log.info(f"Loading initial DDBB configuration for {self.cfg.taskmgr_name}") 
        self.config_tmgr_from_ddbb() 
         
        TaskDB().reset_status()     
        self._load_task_definitions()
        
        if self.cfg.check_configuration_interval>0:
            self.th_check_configuration=PeriodicTask(interval=self.cfg.check_configuration_interval, task_function=self.config_tmgr_from_ddbb)
            self.th_check_configuration.start()
            self.log.info(f"Check DDBB configuration each {self.cfg.check_configuration_interval}seconds")
            


                        
        
    def config_tmgr_from_ddbb(self):
        """config manager

        Args:
            cfg (dict): dict with configuration
        """        
        cfg:Dict=TaskDB().get_task_mgr_configuration(self.app_config["manager_name"]).config
        self.app_config["mgr_config"]=cfg
        self.cfg.task_types=cfg.get("task_types",[])
        
        old_max_wait_count=self.cfg.max_wait_count
        self.cfg.max_wait_count=cfg.get("max_wait_count",10) 
        self.cfg.wait_between_tasks_seconds=cfg.get("wait_between_tasks_seconds",1) 
        self.cfg.monitor_wait_time_seconds=cfg.get("monitor_wait_time_seconds",-1) 
        old_check_configuration_interval=self.cfg.check_configuration_interval
        self.cfg.check_configuration_interval=cfg.get("check_configuration_interval",-1) 
        old_log_level=self.cfg.log_level
        self.cfg.log_level=cfg.get("log_level",logging.INFO) 
        self.log.debug(f"Configuration loaded  for {self.cfg.taskmgr_name}")
        
        #reset data if needed
        if old_log_level!=self.cfg.log_level:
            self.log.setLevel(level=self.cfg.log_level)
            
        if old_max_wait_count!=self.cfg.max_wait_count:
            with self.lock:
                self.max_wait_counter=0
            if self.cfg.max_wait_count==-1:
                self.log.info("Task manager is in infinite mode.")
                
        if self.cfg.check_configuration_interval==0 and self.cfg.check_configuration_interval!=old_check_configuration_interval:
            self.log.info("Stop check DDBB")



        
        
    def _load_task_definitions(self): 
        """load task handlers from config file
        """           
        self.task_definitions=self.app_config.get("task_handlers",{})
        count=0
        if self.task_definitions is None:
            pass
        else:
            count=len(self.task_definitions)
            self.log.info(f"Task definitions loaded from config file: {count}")

    def stop_tasks(self):
        """stop internal threads
        """        
        self.log.debug("Stop threads if needed.")
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
            task_types=self.cfg.task_types
            task=TaskDB(scoped_session=session).get_pending_task(task_types=task_types) 
            return task
        except Exception:
            raise 
        finally:
            db.closeSession()
            
    def task_definition_fetch(self,task_definition):
        """return task definition

        Returns:
            Any: task definition row
        """        
        db=DBBase()
        session = db.getsession()
        try:
            search_type=self.mgr_config.get(LitEnum.task_definition_search_type,LitEnum.CFG_DB)
            task=None
            if search_type in [LitEnum.CFG_ONLY, LitEnum.CFG_DB] :
                task=self.task_definitions[task_definition]
                if task is None and search_type in [LitEnum.CFG_DB] :
                    task=TaskDB(scoped_session=session).get_task_definition(task_type=task_definition) 
            elif search_type in [LitEnum.DB_ONLY,LitEnum.DB_CFG]:
                task=TaskDB(scoped_session=session).get_task_definition(task_type=task_definition)   
                if task is None and search_type in [LitEnum.DB_CFG] :
                    task=self.task_definitions[task_definition]

            if task:
                config=None
                if isinstance(task, dict):
                    config=task.get("config")
                else:
                    config=task.config
                return config
                # return task["config"]
            else:
                raise Exception(f"Task definition not found {task_definition}")
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
        log.info(f"Starting task execution: {id_task}")   
        task_ret=0
        db=DBBase()
        session=db.getsession()
        task_db=TaskDB(scoped_session=session)       
        try:           
            #update task to CHECKING
            resp=task_db.update_status(id=id_task,new_status=TaskStatusEnum.CHECKING,prev_status=TaskStatusEnum.PENDING,output="" )
            if resp["status"]==TaskStatusEnum.CHECKING:   
                launchType:str=""  
                task_obj=self.get_task(id_task)
                task_type=str(task_obj.type).upper()  
                task_ret={} 
                task_config=self.task_definition_fetch(task_definition=task_type)                
                if task_config is None:
                    msg=f"task definition not found: {task_type}"
                    task_db.update_status(id=id_task,new_status=TaskStatusEnum.ERROR,output=msg)
                    return 

                
                launchType=task_config["task_handler"].get("launchType","")
                if not "task_definition" in task_config:
                    task_config["task_definition"]={}
                task_config["task_definition"]["task_id_task"]=str(id_task)
                
                resp=task_db.update_status(id=id_task,new_status=TaskStatusEnum.WAIT_EXECUTION )
                tl=None
                try:
                    tl=TaskLoader(task_config)
                    #-----------START TASK  --------------------
                    
                    task_ret=tl.run_task()
                    #-----------END TASK    --------------------
                    
                    if isinstance(task_ret,dict) is False:
                        task_ret={} 
                        #task handler is not a dict with response data but no error was raised so for us is ok
                    
                    if task_ret.get("status","").upper()=="ERROR":
                        msg=task_ret['message']
                        task_db.update_status(id=id_task,new_status=TaskStatusEnum.ERROR,output=msg) 
                        log.error(f"Task {id_task} launched with errors: {msg}") 
                    else:
                        if launchType.upper()==LitEnum.LAUNCHTYPE_INTERNAL: 
                            #We set task_next_status to FINISHED if it is not informed.
                            task_next_status=task_config["task_handler"].get("task_next_status",TaskStatusEnum.FINISHED) 
                            msg=task_ret.get('message',None)
                            progress=100                                                        
                            task_db.update_status(id=id_task,new_status=task_next_status,output=msg,progress=progress) 
                        log.info(f"Task {id_task} finished.")                     
                    
                    
                except Exception as ex:
                    # here we manage errors inside class, not logical or functional errors that are controlled in task_ret var.
                    msg=str(ex)
                    task_ret['message']=msg
                    task_ret["status"]="ERROR"
                    task_db.update_status(id=id_task,new_status=TaskStatusEnum.ERROR,output=msg,progress=0) 

                task_ret["next_task_wait_seconds"]=task_config.get("next_task_wait_seconds",0)

            else:
                # No se ha podido actualizar, bien porque se ha borrado, porque ya se ha ejecutado, etc. 
                log.warning(f"Task {id_task} not launched. Maybe was deleted or executed in other process.")  
                
            return task_ret

        except Exception as ex:
            self.log.error(f"Task {id_task} raised error {str(ex)}")


    
    def monitor_and_execute(self):
        """check and execute pending tasks
        """                
        try:
            self.max_wait_counter=0
            while True:
                task = self.fetch_pending_tasks()
                if task:
                    task_id = str(task.id)
                    task_ret=self.execute_task(task_id)  
                    next_task_wait_seconds=task_ret.get("next_task_wait_seconds",0)
                    if self.cfg.wait_between_tasks_seconds >0 or next_task_wait_seconds>0: 
                        #When we use this? When the task is executed in a thread, or in flow where we want to wait a time like upscalling resources 
                        if next_task_wait_seconds>  self.cfg.wait_between_tasks_seconds:
                           wait_between_tasks_seconds= next_task_wait_seconds
                        else:
                           wait_between_tasks_seconds =self.cfg.wait_between_tasks_seconds
                        time.sleep(wait_between_tasks_seconds) 
                    self.max_wait_counter=0                     
                else:                    
                    self.max_wait_counter+=1
                    if self.cfg.monitor_wait_time_seconds>0 and self.max_wait_counter==self.cfg.max_wait_count:
                        self.log.info(f"No pending tasks stopping Task manager. Wait time was {str(self.cfg.monitor_wait_time_seconds)} seconds between checks. If you want to deactivate automatic close set max_wait_count=-1")
                        return
                if  self.cfg.monitor_wait_time_seconds>0:   
                    time.sleep(self.cfg.monitor_wait_time_seconds)  # Espera antes de volver a verificar
        finally:
            self.stop_tasks()
    
    






