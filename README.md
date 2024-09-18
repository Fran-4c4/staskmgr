# Simple Task Manager (STMGR)

This is a simple task manager to start processes on AWS/Docker or other platforms. The app includes classes to manage tasks on AWS, but you can implement additional handlers dynamically.

You only need to create a class to handle the task that you want to start and register it in a database (DDBB). Below, I’ll compare STMGR with Celery (since it’s widely used) to explain the key differences and help you make an informed choice.

## Key Differences from Celery

### Task Registration
Celery is based on a broker (like Redis/RabbitMQ) for task queuing and scheduling, requiring you to register tasks with hardcoded definitions. In contrast, STMGR doesn't rely on hardcoded classes; the handlers are dynamically loaded, allowing for changes to modules at any time, as long as they are in an accessible path.

### Broker
- **STMGR**: Relies on a database (Postgres in this case). This design can be extended, but I’ve chosen this for my specific needs.
- **Celery**: Relies heavily on a broker like Redis or RabbitMQ.

### Flexibility
- **STMGR**: More flexible, allowing for configuration changes through a database without deploying new code.
- **Celery**: Task definitions must be present in the codebase (modifying them requires redeployment).

### Distribution
- **STMGR**: Designed with distribution in mind; example tasks can be executed in AWS ECS or Docker. You can create any handler you need with custom configurations stored in a database.
- **Celery**: Focused on task execution using brokers.

### Multiple STMGR Instances
- You can create multiple STMGR instances by configuring them in the database with a key-name. When starting the task manager, specify the key.

---


## Create environment
See https://code.visualstudio.com/docs/python/environments
python3.11 -m venv .venv
or in vscode ctrl+shift+p and python:select interpreter

## Update pip
python -m pip install --upgrade pip

## Install required packages 
```python
pip install -r requirements.txt
```

For development you can install **requirements-dev.txt** too
```python
pip install -r requirements-dev.txt
```

# Application
- Configure application using **appconfig.json**. By default the configuration is outside the application folder in `config` folder.

The application use a DDBB in this case is postgres. You need to configure the conection in **appconfig.json**. Example:
```json
"DDBB_CONFIG": {
		"password": "",
		"port": 5432,
		"host": "",
		"user": "",
		"db": ""
	},
```

To use the package import it as the example below. Please note that you need to pass the configuration to the process. Either a file path or a dictionary:
```python
import tmgr
try:          
    config_like="task_mgr_appconfig.json" 
    curDir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(curDir, 'config', config_like)
    config_like=full_path
    print(f"TASK MANAGER Start" )
    pl=tmgr.TMgr(config_like=config_like)
    pl.monitor_and_execute()
    print(f"TASK MANAGER ENDS" )   
    return process_ret 

except Exception as oEx:
    print('TASK MANAGER Exception [%s]' % str(oEx))
    return "your response or raise exception"
```

# Adding handlers
In order to manage other types you need to create a class and an entry in DDBB or in your appconfig.json in the section **task_handlers**. When the task is retrieved from DDBB it will look the handler.

```JSON
{...
	,"task_handlers":{
		"TestTaskHandler":{
			"name": "Test task",
            "module": "TestTaskHandler",
            "class": "TestTaskHandler",
            "path": "path_to/task_handlers" //Folder
		}
    }
```

# DDBB configuration
You need a DDBB with 2  tables:
- tmgr_tasks: Info with the task
- tmgr_tasks_dep: Info with task dependencies needed by task to be exceuted.
See table creation in config\ddbb_script.sql

# Test in local 
Install using pip in your project using
pip install "path_to_dist/dist/Simple_Task_Manager-0.1.0-py3-none-any.whl"
