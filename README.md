# Simple Task Manager (STMGR)

This is a simple task manager to start processes on AWS/Docker or other platforms. The app includes classes to manage tasks on AWS, but you can implement additional handlers dynamically.

You only need to create a class to handle the task that you want to start and register it in a database (DDBB). Below, I'll compare STMGR with Celery (since it's widely used) to explain the key differences and help you make an informed choice. Another good choice is Dramatiq. For a simple comparison between STMGR and Celery check 

## Installation
This project can be installed using pip:

```python
pip install simple-task-manager

```
Or it can be installed directly from git:
pip install git+https://github.com/Fran-4c4/staskmgr


## Usage
- First you need to configure the minimum parameters in order to run tasks. See  [Configuration](./docs/configuration.md)
- Second you need a database to store configuration and task management. See table creation in folder config\ddbb_script.sql or [Configuration scripts](./docs/configuration_sql.md)



More info in github [GitHub](https://github.com/Fran-4c4/staskmgr).

---

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
You need a DDBB with the configuration:



# Test in local 
Install using pip in your project using
pip install "path_to_dist/dist/Simple_Task_Manager-0.1.0-py3-none-any.whl" 

The wheel can be diferent after creating building.

## License
licensed under Apache License 2.0
