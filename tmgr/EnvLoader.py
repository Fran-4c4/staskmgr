

import os
from dotenv import load_dotenv
from pathlib import Path

class EnvLoader():

    def __init__(self,app_name,env_name=None) -> None:
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

        # Now you can access environment variables
        # DDBB_CONFIG = os.getenv('DDBB_CONFIG') 
        print("Environment vars loaded")       
