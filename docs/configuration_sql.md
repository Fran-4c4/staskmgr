# Simple Task Manager (STMGR)

## DDBB sql script creation

```javascript

-- DROP TABLE public.tmgr_config;

CREATE TABLE public.tmgr_config (
	id text NOT NULL,
	"name" text NOT NULL,
	config jsonb NULL,
	description text NULL,
	CONSTRAINT tmgr_config_pk PRIMARY KEY (id)
);


-- DROP TABLE public.tmgr_tasks;

CREATE TABLE public.tmgr_tasks (
	id uuid DEFAULT uuid_generate_v1() NOT NULL,
	id_tmgr text DEFAULT 'MAIN'::text NOT NULL,
	status text NULL,
	progress int4 NULL,
	"type" text NOT NULL,
	parameters jsonb NULL,
	time_start timestamp NULL,
	time_end timestamp NULL,
	"output" text NULL,
	created_at timestamp DEFAULT timezone('UTC'::text, now()) NULL,
	priority int2 DEFAULT 0 NULL,
	modify_date timestamptz DEFAULT now() NULL,
	scheduled_date timestamp DEFAULT now() NULL,
	recurrence_interval varchar DEFAULT '1'::character varying NULL,
	CONSTRAINT tmgr_tasks_pkey PRIMARY KEY (id)
);
CREATE INDEX tmgr_tasks_id_tmgr_idx ON public.tmgr_tasks USING btree (id_tmgr);
CREATE INDEX tmgr_tasks_time_start_idx ON public.tmgr_tasks USING btree (time_start);
CREATE INDEX tmgr_tasks_type_idx ON public.tmgr_tasks USING btree (type);


--CONSTRAINT tmgr_tasks_tmgr_task_definitions_fk FOREIGN KEY ("type") REFERENCES public.tmgr_task_definitions(id)

-- DROP TABLE public.tmgr_task_dep;

CREATE TABLE public.tmgr_task_dep (
	id_task uuid NOT NULL,
	id_task_dep uuid NOT NULL,
	CONSTRAINT tmgr_task_dep_pk PRIMARY KEY (id_task, id_task_dep),
	CONSTRAINT tmgr_task_dep_id_task_dep_fkey FOREIGN KEY (id_task_dep) REFERENCES public.tmgr_tasks(id) ON DELETE CASCADE,
	CONSTRAINT tmgr_task_dep_id_task_fkey FOREIGN KEY (id_task) REFERENCES public.tmgr_tasks(id) ON DELETE CASCADE
);

-- DROP TABLE public.tmgr_task_definitions;
CREATE TABLE public.tmgr_task_definitions (
	id text NOT NULL,
	"name" text NOT NULL,
	active bool DEFAULT true NOT NULL,
	config jsonb NULL,
	CONSTRAINT tmgr_task_definitions_pk PRIMARY KEY (id)
);
CREATE UNIQUE INDEX tmgr_task_definitions_idx_id_caseinsensitive ON public.tmgr_task_definitions USING btree (lower(id));

-- DROP TABLE public.tmgr_mgr_definitions;

CREATE TABLE public.tmgr_mgr_definitions (
	id_mgr text NOT NULL,
	id_task_definition text NOT NULL,
	CONSTRAINT tmgr_mgr_definitions_pk PRIMARY KEY (id_mgr, id_task_definition)
);

-- DROP TABLE public.tmgr_logs;

CREATE TABLE public.tmgr_logs (
	id serial4 NOT NULL,
	"timestamp" timestamp NOT NULL,
	"level" varchar(10) NOT NULL,
	"name" varchar(100) NOT NULL,
	message text NULL,
	origin text NULL,
	CONSTRAINT tmgr_logs_pk PRIMARY KEY (id)
);

--EXAMPLE configuration
INSERT INTO public.tmgr_config
(id, "name", config, description)
VALUES('MAIN_MGR', 'MAIN_MGR', '{"task_types": ["TEST_MGR"], "max_wait_count": 2, "monitor_wait_time_seconds": 10, "wait_between_tasks_seconds": 5, "task_definition_search_type": "DB_CFG", "check_configuration_interval": 10}'::jsonb, 'Main manager for general tasks');

--EXAMPLE TASK
INSERT INTO public.tmgr_task_definitions
(id, "name", active, config)
VALUES('TEST_MGR', 'TEST_MGR', true, '{"task_handler": {"name": "TestTaskHandler", "path": "task_handlers", "class": "TestTaskHandler", "module": "test_task_handler", "launchType": "INTERNAL", "task_next_status": "FINISHED"}}'::jsonb);

```
