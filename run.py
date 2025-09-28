import json
import os
import sys
import logging
from typing import Dict
import urllib.parse
from dotenv import load_dotenv
from pathlib import Path


from tmgr import TMgr
from tmgr.configuration_helper import ConfigurationHelper
from tmgr.log_handlers.postgres_handler import  PostgreSQLHandler
from tmgr.log_handlers.origin_filter import OriginFilter

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def file_get_absolute_path(file_path:str):
    """return full file path if the file_path is relative or absolute.

    Args:
        file_path (str): file path

    Returns:
        str: absolute path
    """    
    if file_path:               
        # Check if the path is absolute
        if not os.path.isabs(file_path):
            # If it's not absolute, resolve it relative to the application path
            app_path =sys.path[0] #os.path.dirname(os.path.abspath(__file__))  # Application's base directory
            file_path = os.path.abspath(os.path.join(app_path, file_path))  # Resolve the relative path
            return file_path
        else:
            return file_path

def load_env(app_name,env_name,env_folder=".envs") -> None:
    # Get the user's home directory
    home_dir = Path(os.path.expanduser('~'))

    # Get the environment from the ENVIRONMENT variable, default to 'development'
    environment = os.getenv('ENVIRONMENT',env_name )
    print(f"Environment is {environment}")    

    # Build the path to the environment file (e.g., .env.development or .env.production or .env.DEV)
    fname=f'.env.{app_name}'
    if environment:
        fname+="." + environment
    env_file = home_dir / env_folder / fname

    # Load the environment file
    load_dotenv(dotenv_path=env_file)

    print("Environment vars loaded")   


def init_logging(cfg:Dict):
    # Remove logging.basicConfig because it may override your manual settings
    log_cfg=cfg.get("logging", {})
    log_level=log_cfg.get("DEFAULT_LOG_LEVEL",logging.DEBUG) 
    logger = logging.getLogger()
    logger.setLevel( log_level) 


    # Define formatter with custom 'origin' field
    formatter_str=log_cfg.get("DEFAULT_LOG_FORMATTER","'%(asctime)s -  %(levelname)s - %(name)s-%(funcName)s.%(lineno)d - %(message)s - origin: %(origin)s'") 
    formatter = logging.Formatter(formatter_str)

    # Apply the custom filter with 'origin' field
    origin_filter = OriginFilter(origin=cfg.get("manager_name", "staskmgr"))
    log_file=log_cfg.get("LOGFILE")

    # Create handlers
    file_handler = logging.FileHandler(log_file)
    console_handler = logging.StreamHandler()
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    for handler in logger.root.handlers:
        # This is lazy and does only the minimum alteration necessary. It'd be better to use
        # dictConfig / fileConfig to specify the full desired configuration from the start:
        # http://docs.python.org/2/library/logging.config.html#dictionary-schema-details
        # handler.setFormatter(CustomFormatter(handler.formatter._fmt))
        handler.setLevel(log_level)
        handler.addFilter(origin_filter)
        handler.setFormatter(formatter)

    # Optionally add the PostgreSQL handler
    db_handler_cfg=log_cfg.get("DB_HANDLER",{})
    use_db_handler = bool(db_handler_cfg.get("USE_DB_HANDLER", "False"))
    if use_db_handler:
        try:
            # Configurar el DSN para PostgreSQL
            dbcfg = cfg.get('DDBB_CONFIG') 
                       
            dbcfg["LOG_LEVEL"]=db_handler_cfg.get("LOG_LEVEL", logging.DEBUG)
            dbcfg["DEFAULT_LOG_FORMATTER"]=formatter
            dbcfg["TMGR_LOG_TABLE"]=db_handler_cfg.get("TMGR_LOG_TABLE", "tmgr_logs")
            pg_handler = PostgreSQLHandler(config=dbcfg) 
            logger.addHandler(pg_handler)

        except Exception as ex:
            print(f'WARNING: DDBB log handler error {str(ex)}')


if __name__ == "__main__":

    load_env(app_name="stmgr",env_name="DEV")
    config_like=os.getenv("stmgr_config_file", "config/appconfig.json" )
    full_path=file_get_absolute_path(file_path=config_like)
    config_like=full_path
    print(f"Config file: {full_path}")
    cfg=ConfigurationHelper().load_config(config_like=config_like)

    try:           
        init_logging(cfg=cfg)#this is an example method on how to configure logs. You can do whatever you want. STMGR will log to default logger.
        logger = logging.getLogger(__name__)
        logger.info('Starting run.py demo entrypoint.')
        pl=TMgr(config_like=config_like)
        
        pl.monitor_and_execute()

        print("TASK MANAGER ENDS" )   

    except Exception as oEx:
        print('TASK MANAGER Exception [%s]' % str(oEx))
