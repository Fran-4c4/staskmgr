Simple Task Manager (STMGR)
========================

This is a simple task manager to start process on AWS/Docker or other places.
The app has built some classes to manage the run on AWS but you can implement more and use dinamically.
You only need to create a class to handle the task that you need to start and register in a DDBB.
I´m going to compare with Celery(because is one of the most used) in order to explain the main diferences so you can choose right.
What is the main diference with Celery for example? Celery is based on a Broker (like Redis/RabbitMQ) for task queuing and scheduling and need to register the task in celery using hardcode. STMGR don´t depends on hardcode the class inside. The handlers are loaded dinamically so the modules can be changed at any time and loaded from everywhere(not at all in this version because the classes must be in an accesible path).
**Broker**
STMGR relies in database(postgres in this case). Celery relies heavily on a broker (like Redis/RabbitMQ) for task queuing and scheduling. Your task manager may or may not need this depending on your design. STMGR coud be extend this functionality but due to my own needs i use this way.
**Flexibility**
STMGR is more flexible in that it allows for configuration changes through a database, meaning you can modify task behavior without deploying new code. Celery requires that task definitions be present in the codebase (though you can modify them by redeploying).
**Distribution**
STMGR is designed with distribution in mind so the exaple tasks are designed to be executed in AWS ECS or Docker. You can create wathever handler you need including his own configuration in diferent database.
**Multiple STMG**
You can create multiple STMGR. Simply configure them in database with a key-name. When you start the task manager you can tell the key.
---------------


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
