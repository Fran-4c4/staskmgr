import json
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from tmgr.enums.lit_enum import LitEnum

@dataclass
class Config:
    """library configuration

    """
    taskmgr_name: str = field(default="", metadata={"description": "Task manager name"})   
    DDBB_CONFIG:Dict = field(default_factory=dict, metadata={"description": "DDBB configuration"})
    task_types: List[str] = field(default_factory=list, metadata={"description": "List of task types available"})
    max_wait_count:int=field(default=2, metadata={"description": "Time in seconds to wait"})
    monitor_wait_time_seconds: int = field(default=10, metadata={"description": "Monitor wait time"})
    wait_between_tasks_seconds: int = field(default=5, metadata={"description": "wait between tasks seconds"})
    task_definition_search_type: int = field(default=LitEnum.DB_CFG, metadata={"description": "task_definition_search_type"})
    check_configuration_interval: int = field(default=-1, metadata={"description": "Check configuration interval. If -1 then check is disabled."})
    log_level: int = field(default=logging.DEBUG, metadata={"description": "Log level for tmgr package."})
    test_mode: bool = field(default=False, metadata={"description": "Active debug mode"})
    
    # def __post_init__(self):
    #     pass
    
    def load_parse_cfg_file(self,config_like):
        config_data=None
        if isinstance(config_like, str) and os.path.exists(config_like):
            config_data = self._load_file(file_path=config_like)               
        elif isinstance(config_like, dict):
            config_data = config_like
        else:
            raise ValueError("config_like must be path to config file or JSON object.")
        
        self._asign_values(config_data=config_data)
        
    
    def _load_file(self, file_path):
        """
        load JSON from file path.
        """
        with open(file_path, 'r', encoding='utf-8') as mfile:
            return json.load(mfile)
    
    def _asign_values(self,config_data):     
        # assign values to class
        for key, value in config_data.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                setattr(self, key, value)

    def __repr__(self):
        # Para representar la configuración en un formato legible
        return f"Config(task_definition_search_type={self.task_definition_search_type}, check_configuration_interval={self.check_configuration_interval})"
