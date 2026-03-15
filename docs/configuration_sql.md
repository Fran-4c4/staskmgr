# Simple Task Manager (STMGR)

## DDBB sql script creation

Use these scripts:

- Fresh install: `config/ddbb_script.sql`
- Upgrade from 1.5.x: `config/ddbb_upgrade_1_6.sql`

## New columns added in 1.6
- `claimed_by`
- `claim_token`
- `heartbeat_at`
- `lease_until`
- `attempt`
- `external_ref`
- `last_error`

These columns are additive and do not break current clients that still read the old schema fields only.

## Upgrade notes
1. Apply `config/ddbb_upgrade_1_6.sql`.
2. Keep `compatibility_mode=AUTO` during rollout.
3. Switch to `SAFE` only after validating the service deployment.
