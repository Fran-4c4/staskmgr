import os
import json
from typing import Any

class ConfigurationHelper():
    """Basic class to load configuration     
    """    
    config=None

    def load_config(self,config_like:Any)->dict:
        """ 

        Reads the json file with the app config and return a dict with the configuration.

        Args:
            config_like (Any): config_like must be path to config file or JSON object.
        Returns:
            dict: configuration
        """     

        cfg = self.load_parse_cfg_file(config_like=config_like)   
        self.config=cfg

        keys=cfg.keys()
        for k in keys:
            self.update_field_with_environment(k)

        # special cases use from caller this method
        # self.updatefieldWithEnvironment("DDBB_CONFIG","db")
        return cfg
    
    def load_parse_cfg_file(self,config_like):
        config_data=None
        if isinstance(config_like, str) and os.path.exists(config_like):
            config_data = ConfigurationHelper().load_file(file_path=config_like)               
        elif isinstance(config_like, dict):
            config_data = config_like
        else:
            raise ValueError("config_like must be path to config file or JSON object.")
        
        return config_data
    
    def load_file(self, file_path):
        """
        load JSON from file path.
        """
        with open(file_path, 'r', encoding='utf-8') as mfile:
            return json.load(mfile)

    def update_field_with_environment(self,env_key, config_key=None):
        if config_key is None:
            config_key=env_key #cuando se llaman igual    
        new_value = os.environ.get(env_key)
        if new_value is not None:	
            try:
                new_value_dict = json.loads(new_value)
                new_value=new_value_dict
            except Exception as ex:
                pass #the value is string
                
            self.config[config_key]=new_value
