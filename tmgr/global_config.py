"""globalconfig  store basic data from app_config.json file and is used to share common data in the project

 """
class GlobalConfig:
    app_config = {
        "config_file": "appconfig.json"
    }

# Create a global instance for configuration
gconfig = GlobalConfig()
