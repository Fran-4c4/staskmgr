ALTER TABLE public.tmgr_tasks ADD COLUMN IF NOT EXISTS claimed_by text NULL;
ALTER TABLE public.tmgr_tasks ADD COLUMN IF NOT EXISTS claim_token text NULL;
ALTER TABLE public.tmgr_tasks ADD COLUMN IF NOT EXISTS heartbeat_at timestamptz NULL;
ALTER TABLE public.tmgr_tasks ADD COLUMN IF NOT EXISTS lease_until timestamptz NULL;
ALTER TABLE public.tmgr_tasks ADD COLUMN IF NOT EXISTS attempt int4 DEFAULT 0 NULL;
ALTER TABLE public.tmgr_tasks ADD COLUMN IF NOT EXISTS external_ref text NULL;
ALTER TABLE public.tmgr_tasks ADD COLUMN IF NOT EXISTS last_error text NULL;

CREATE INDEX IF NOT EXISTS tmgr_tasks_status_priority_created_idx
ON public.tmgr_tasks USING btree (status, priority DESC, created_at ASC);

CREATE INDEX IF NOT EXISTS tmgr_tasks_lease_until_idx
ON public.tmgr_tasks USING btree (lease_until);

CREATE INDEX IF NOT EXISTS tmgr_tasks_claim_token_idx
ON public.tmgr_tasks USING btree (claim_token);
