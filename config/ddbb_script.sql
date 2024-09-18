

-- DROP TABLE public.process;

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
	CONSTRAINT tmgr_tasks_pkey PRIMARY KEY (id)
);
CREATE INDEX tmgr_tasks_id_tmgr_idx ON public.tmgr_tasks USING btree (id_tmgr);
CREATE INDEX tmgr_tasks_time_start_idx ON public.tmgr_tasks USING btree (time_start);
CREATE INDEX tmgr_tasks_type_idx ON public.tmgr_tasks USING btree (type);

--CONSTRAINT tmgr_tasks_tmgr_task_definitions_fk FOREIGN KEY ("type") REFERENCES public.tmgr_task_definitions(id)

CREATE TABLE public.tmgr_task_dep (
	id_task uuid NOT NULL,
	id_task_dep uuid NOT NULL,
	CONSTRAINT tmgr_task_dep_pk PRIMARY KEY (id_task, id_task_dep),
	CONSTRAINT tmgr_task_dep_id_task_dep_fkey FOREIGN KEY (id_task_dep) REFERENCES public.tmgr_tasks(id) ON DELETE CASCADE,
	CONSTRAINT tmgr_task_dep_id_task_fkey FOREIGN KEY (id_task) REFERENCES public.tmgr_tasks(id) ON DELETE CASCADE
);

-- optional you can create process definitions in DDBB

-- DROP TABLE public.tmgr_task_definitions;
CREATE TABLE public.tmgr_task_definitions (
	id text NOT NULL,
	"name" text NOT NULL,
	active bool DEFAULT true NOT NULL,
	config jsonb NULL,
	CONSTRAINT tmgr_task_definitions_pk PRIMARY KEY (id)
);
CREATE UNIQUE INDEX tmgr_task_definitions_idx_id_caseinsensitive ON public.tmgr_task_definitions USING btree (lower(id));

--EXAMPLE TASK
INSERT INTO public.tmgr_task_definitions
(id, "name", active, config)
VALUES('TEST_MGR', 'TEST_MGR', true, '{"task_handler": {"name": "TEST_MGR"
, "path": "/taskmgr/task_handlers", "class": "TestTaskHandler", "module": "TestTaskHandler", "launchType": "INTERNAL"}, "task_definition": {"data":"data_needed_to_execute"}}'::jsonb);