# Docker notes

STMGR is usually deployed as a service inside Docker.

## Base image
Use Python 3.10 or newer.

## Upgrade
1. Apply `config/ddbb_upgrade_1_6.sql` in PostgreSQL.
2. Rebuild the image with STMGR 1.6.0.
3. Start with `compatibility_mode=AUTO`.
4. Switch to `SAFE` after validation.

## DockerTaskHandler modes
- `DETACHED` is the default and is recommended for heavy containers.
- `BLOCKING` waits for container completion and is intended for lighter workloads.
- Detached tasks can be reconciled later by STMGR when `external_ref` is available in the upgraded schema.

See [docs/docker_handler.md](../docs/docker_handler.md).

## Local test image
This folder includes a minimal test Dockerfile.
