# Docker Handler

`DockerTaskHandler` supports two execution modes.

## Default mode
`execution_mode=DETACHED`

This is the default and is intended for heavy containers.

Behavior:
- Launch the container and return immediately.
- Return `external_ref` with the full Docker container id.
- Mark the STMGR task as deferred so the manager does not finish it inline.
- `container_remove` defaults to `false` in this mode.
- `capture_logs` defaults to `false` in this mode.
- STMGR can reconcile the container later and update `WAIT_EXECUTION -> FINISHED/ERROR`.

## Blocking mode
`execution_mode=BLOCKING`

Use this for lightweight containers when STMGR should wait for completion.

Behavior:
- Wait for the container to finish.
- Treat non-zero exit code as task error.
- `container_remove` defaults to `true` in this mode.
- `capture_logs` defaults to `true` in this mode.

## Backward compatibility
- `wait_for_completion=true` is still supported and maps to `execution_mode=BLOCKING`.
- If `execution_mode` is omitted, the handler uses `DETACHED`.

## Reconciliation
Detached reconciliation requires the upgraded schema introduced in 1.6 and `compatibility_mode=AUTO` or `SAFE`.

Recommended manager settings:

```json
{
  "compatibility_mode": "AUTO",
  "external_reconcile_interval_seconds": 30,
  "external_reconcile_batch_size": 10
}
```

Behavior:
- STMGR stores the full Docker container id in `external_ref`.
- The manager periodically claims tasks in `WAIT_EXECUTION` and asks the handler to reconcile them.
- If the container is still running, the task stays in `WAIT_EXECUTION`.
- If the container exits with code `0`, the task moves to `FINISHED` or `task_next_status`.
- If the container exits with a non-zero code, the task moves to `ERROR`.

Important:
- In detached mode, keep `container_remove=false` if you want STMGR to reconcile the real container state later.
- If the container disappears before reconciliation, STMGR will mark the task as error.

## Recommended examples

### Heavy container
```json
{
  "task_handler": {
    "name": "DockerTaskHandler",
    "path": "task_handlers",
    "class": "DockerTaskHandler",
    "module": "docker_task_handler",
    "launchType": "INTERNAL"
  },
  "task_definition": {
    "image": "my-heavy-image:latest",
    "execution_mode": "DETACHED",
    "container_remove": false,
    "networks": ["my-network"]
  }
}
```

### Lightweight container
```json
{
  "task_handler": {
    "name": "DockerTaskHandler",
    "path": "task_handlers",
    "class": "DockerTaskHandler",
    "module": "docker_task_handler",
    "launchType": "INTERNAL",
    "task_next_status": "FINISHED"
  },
  "task_definition": {
    "image": "my-light-image:latest",
    "execution_mode": "BLOCKING",
    "wait_timeout_seconds": 900,
    "capture_logs": true,
    "log_max_bytes": 65536
  }
}
```

## Optional fields
- `execution_mode`: `DETACHED` or `BLOCKING`
- `wait_for_completion`: legacy alias for `BLOCKING`
- `wait_timeout_seconds`: only used in `BLOCKING`
- `capture_logs`: collect logs on completion
- `log_max_bytes`: cap for returned logs
- `container_remove`: whether Docker should remove the container
- `name`: optional base name; STMGR appends a unique suffix unless placeholders are used

Placeholders supported in `name`:
- `<idtask>`
- `<timestamp>`
