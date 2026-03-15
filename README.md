# Simple Task Manager (STMGR)

This is a simple task manager to start processes on AWS/Docker or other platforms. The app includes classes to manage tasks on AWS, but you can implement additional handlers dynamically.

You only need to create a class to handle the task that you want to start and register it in a database (DDBB). Below, I'll compare STMGR with Celery (since it's widely used) to explain the key differences and help you make an informed choice. Another good choice is Dramatiq. For a simple comparison between STMGR and Celery check 

## Requirements
- Python 3.10 or newer
- PostgreSQL
- `psycopg[binary]`

## Installation
This project can be installed using pip:

```python
pip install simple-task-manager

```
Or it can be installed directly from git:
pip install git+https://github.com/Fran-4c4/staskmgr

## Upgrade from 1.5.x
- Existing client code using `TaskDB` can remain synchronous.
- The service runtime now uses an async SQLAlchemy layer internally.
- Backward compatibility is preserved through compatibility modes:
  - `LEGACY`: old behavior only
  - `AUTO`: use safe mode when the upgraded schema is available
  - `SAFE`: require the upgraded schema and enable lease-based recovery
- To upgrade an existing installation, apply [config/ddbb_upgrade_1_6.sql](./config/ddbb_upgrade_1_6.sql) before enabling `SAFE` mode.

See [Upgrade guide](./docs/upgrade_1_6.md).

## Usage and requirements
- First you need to configure the minimum parameters in order to run tasks. See  [Configuration](./docs/configuration.md)
- Second you need a database to store configuration and task management. See table creation in folder `config/ddbb_script.sql` or [Configuration scripts](./docs/configuration_sql.md). Actually only PostgreSQL is supported.



More info in github [GitHub](https://github.com/Fran-4c4/staskmgr).

---

# Adding handlers
In order to manage other types you need to create a class and an entry in DDBB or in your appconfig.json in the section **task_handlers**. When the task is retrieved from DDBB it will look the handler. Below is an example of the Test task handler.

```JSON

"task_handlers": {
    "TEST_MGR": {
      "config": {
        "task_handler": {
          "name": "TestTaskHandler",
          "path": "task_handlers",
          "class": "TestTaskHandler",
          "module": "test_task_handler",
          "launchType": "INTERNAL",
		      "task_next_status":"FINISHED"
        }
      }
    }
  }
```

# Test in local 
Install using pip in your project using the next command and changing x.x.x version.

```console
pip install "path_to_dist/dist/Simple_Task_Manager-x.x.x-py3-none-any.whl" 
```

## Sphinx documentation
- There is a minimal documentation generated from source. See  [Documentation](./docs/sphinx.md)

## Running as a Docker service
STMGR is normally deployed as a service inside Docker.

1. Build an image based on Python 3.10 or newer.
2. Install the package version you want to run.
3. Mount the configuration and provide database credentials.
4. Apply the SQL upgrade before enabling `SAFE` mode.

See [Docker notes](./docker/README.md).

## Docker handler modes
`DockerTaskHandler` now supports two modes:

- `DETACHED`: default mode, intended for heavy containers. Launch and return immediately.
- `BLOCKING`: wait for the container to finish. Intended for lightweight containers.
- In `DETACHED`, STMGR can later reconcile the container state using `external_ref` when the upgraded schema is enabled.

See [Docker handler guide](./docs/docker_handler.md).

# License
licensed under Apache License 2.0
