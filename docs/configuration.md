# Simple Task Manager (STMGR)

## Configuration
This application use a DDBB for configuration. You need to configure the conection in a json file or pass directly in a dict configuration. Example:
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
from tmgr import TMgr
try:          
    config_like="task_mgr_appconfig.json" 
    pl=tmgr.TMgr(config_like=config_like)
    pl.monitor_and_execute()
except Exception as oEx:
    print('TASK MANAGER Exception [%s]' % str(oEx))
    return "your response or raise exception"
```

## Database tables
There are some tables needed for STMGR to work.

<table>
  <tr>
    <th>Table</th>
    <th>Description</th>
  </tr>
  <tr>
    <td>tmgr_config</td>
    <td>Configuration for each STMGR. This table is used to retrieve configuration automatically at intervals. Can be disabled/enable in configuration.</td>
  </tr>
  <tr>
    <td>tmgr_task_definitions</td>
    <td>Configuration how a task is launched.</td>
  </tr>
  <tr>
    <td>tmgr_mgr_definitions</td>
    <td>Wich tasks can be launched by each STMGR. Task can be configured in application configuration too.</td>
  </tr>  
  <tr>
    <td>tmgr_tasks</td>
    <td>Tasks created to be launched. Those tasks are created by other applications and include configuration when needed.</td>
  </tr>  
  <tr>
    <td>tmgr_task_dep</td>
    <td>Tasks dependency, task can not be started when they depend on others. STMGR handles this for you but it can be easily coded in your own task handlers.</td>
  </tr>     
</table>