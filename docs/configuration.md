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

## New runtime compatibility settings
The service can run in three compatibility modes without breaking current clients:

- `LEGACY`: current behavior based on status transitions only.
- `AUTO`: enables lease-based recovery when the upgraded schema is present.
- `SAFE`: requires the upgraded schema and enables the safer recovery flow.

Recommended manager configuration in `tmgr_config.config`:

```json
{
  "compatibility_mode": "AUTO",
  "lease_timeout_seconds": 300,
  "task_heartbeat_interval": 30,
  "external_reconcile_interval_seconds": 30,
  "external_reconcile_batch_size": 10
}
```

Notes:
- Existing applications using `TaskDB` synchronously do not need to migrate to async.
- The STMGR service uses SQLAlchemy async internally.
- If you enable `SAFE`, first apply the SQL migration in `config/ddbb_upgrade_1_6.sql`.
- Reconciliation of detached external tasks requires the upgraded schema and `AUTO` or `SAFE` mode.

## Docker task handler
`DockerTaskHandler` now supports `DETACHED` and `BLOCKING` modes.

- `DETACHED` is the default and is intended for heavy containers.
- `BLOCKING` waits for the container to finish and should be used for lightweight containers.
- `wait_for_completion=true` is still accepted for backward compatibility and maps to `BLOCKING`.

See [Docker handler guide](./docker_handler.md).

## Database tables
There are some tables needed for STMGR to work. The script for this tables is in file **ddbb_script.sql** config folder. See table creation in folder config\ddbb_script.sql or [Configuration scripts](./configuration_sql.md)

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
