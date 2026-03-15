# Upgrade to 1.6

## Summary
Version 1.6 keeps backward compatibility for current clients while improving service safety and moving the STMGR runtime to SQLAlchemy async internally.

## What changes
- Minimum Python version becomes 3.10.
- STMGR service runtime uses async SQLAlchemy internally.
- `TaskDB` remains available as a synchronous API for current clients.
- The PostgreSQL schema gets additive columns for lease-based recovery.
- Detached Docker tasks can now be reconciled later using `external_ref`.

## Upgrade steps for existing users
1. Upgrade the Python runtime to 3.10 or newer.
2. Apply `config/ddbb_upgrade_1_6.sql` in PostgreSQL.
3. Upgrade the package:

```bash
pip install -U simple-task-manager==1.6.0
```

4. Deploy the service with `compatibility_mode=AUTO`.
5. Validate logs and task processing.
6. Optionally move to `compatibility_mode=SAFE`.

## Docker deployments
1. Use a Python 3.10+ base image.
2. Rebuild the image with STMGR 1.6.0.
3. Run the SQL upgrade before enabling `SAFE`.

## Compatibility modes
- `LEGACY`: old behavior, no lease-based recovery.
- `AUTO`: safe mode if the schema upgrade is present; legacy otherwise.
- `SAFE`: requires the upgraded schema and enables the safer flow.

## Rollback
If you need to rollback the service package, keep the extra columns in PostgreSQL. They are additive and do not break 1.5.x clients reading the old fields.
