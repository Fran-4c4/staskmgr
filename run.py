import json
import os
import logging
import urllib.parse
from dotenv import load_dotenv
from pathlib import Path


from tmgr import TMgr
from tmgr.log_handlers.postgres_handler import  PostgreSQLHandler
from tmgr.log_handlers.origin_filter import OriginFilter

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_env(app_name="staskmgr",env_name="DEV") -> None:
    # Get the user's home directory
    home_dir = Path(os.path.expanduser('~'))

    # Get the environment from the ENVIRONMENT variable, default to 'development'
    environment = os.getenv('ENVIRONMENT',env_name )
    print(f"Environment is {environment}")    

    # Build the path to the environment file (e.g., .env.development or .env.production)
    fname=f'.env.{app_name}'
    if environment:
        fname+="." + environment
    env_file = home_dir / '.envs' / fname

    # Load the environment file
    load_dotenv(dotenv_path=env_file)

    print("Environment vars loaded")   


def init_logging():
    # Remove logging.basicConfig because it may override your manual settings
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG) 

    # Define formatter with custom 'origin' field
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s - origin: %(origin)s')

    # Apply the custom filter with 'origin' field
    origin_filter = OriginFilter(origin='staskmgr')


    # Create handlers
    file_handler = logging.FileHandler('app.log')
    console_handler = logging.StreamHandler()

    # Optionally add the PostgreSQL handler
    use_db_handler = bool(os.getenv("USE_DB_HANDLER", "False"))
    if use_db_handler:
        try:
            # Configurar el DSN para PostgreSQL
            dbcfg = json.loads(os.environ.get('DDBB_CONFIG'))
            user = dbcfg.get('user')
            password = dbcfg.get('password')
            host = str(dbcfg.get('host'))
            port = str(dbcfg.get('port'))
            db_name = str(dbcfg.get('db'))

            dsn = f"dbname={db_name} user={user} password={password} host={host} port={port}"

            pg_handler = PostgreSQLHandler(
                dsn,
                table_name='tmgr_logs',
            )    
            # pg_handler.setLevel(logging.DEBUG)
            # pg_handler.setFormatter(formatter)
            logger.addHandler(pg_handler)

        except Exception as ex:
            print(f'WARNING: DDBB log handler error {str(ex)}')

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    for handler in logger.root.handlers:
        # This is lazy and does only the minimum alteration necessary. It'd be better to use
        # dictConfig / fileConfig to specify the full desired configuration from the start:
        # http://docs.python.org/2/library/logging.config.html#dictionary-schema-details
        # handler.setFormatter(CustomFormatter(handler.formatter._fmt))
        handler.setLevel(logging.DEBUG)
        handler.addFilter(origin_filter)
        handler.setFormatter(formatter)

if __name__ == "__main__":

    load_env()
    config_like="appconfig.json" 
    curDir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(curDir, 'config', config_like)
    config_like=full_path

    try:           
        init_logging()
        logger = logging.getLogger(__name__)
        logger.info('Starting run.py demo.')
        pl=TMgr(config_like=config_like)
        
        pl.monitor_and_execute()

        print("TASK MANAGER ENDS" )   

    except Exception as oEx:
        print('TASK MANAGER Exception [%s]' % str(oEx))
