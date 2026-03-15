import asyncio
import logging
import threading
import uuid
from typing import Dict

import tmgr
from tmgr.enums.lit_enum import FilterTaskKeyEnum
from tmgr.model.config import Config

from .async_task_db import AsyncTaskDB
from .configuration_helper import ConfigurationHelper
from .db_mgr import DBMgr
from .enums import CFGOrderEnum, LitEnum
from .enums.task_status_enum import TaskStatusEnum
from .global_config import gconfig
from .periodic_task import PeriodicTask
from .task_db import TaskDB
from .task_loader import TaskLoader


class TMgr:
    """Class to manage tasks stored in DDBB."""

    configuration_file = None
    task_definitions = {}
    th_check_configuration = None
    tasks_active = []
    lock = threading.Lock()

    def __init__(self, config_like: any, taskmgr_name="staskmgr"):
        self.log = logging.getLogger(__name__)
        self.version = tmgr.__version__
        self.log.info(f"Starting STMR for {taskmgr_name} {self.version}")
        self.cfg = Config()
        self.cfg.taskmgr_name = taskmgr_name
        self.configuration_file = config_like
        self.max_wait_counter = 0
        self.schema_capabilities = {
            "task_columns": set(),
            "supports_lease_columns": False,
        }
        self.manager_instance_id = f"{taskmgr_name}:{uuid.uuid4().hex[:8]}"
        self.last_external_reconcile_at = None

        self.init_configuration(config_like=config_like)

    @property
    def app_config(self):
        return gconfig.app_config

    @app_config.setter
    def app_config(self, value):
        gconfig.app_config = value

    @property
    def mgr_config(self):
        return gconfig.app_config.get("mgr_config", {})

    def init_configuration(self, config_like: any):
        cfgh = ConfigurationHelper()
        self.app_config = cfgh.load_config(config_like=config_like)
        self.cfg.load_parse_cfg_file(config_like=self.app_config)
        self.cfg.taskmgr_name = self.app_config["manager_name"]

        DBMgr().init_database(self.cfg.DDBB_CONFIG)
        self.log.info(f"Loading initial DDBB configuration for {self.cfg.taskmgr_name}")

        self.config_tmgr_from_ddbb()
        self.schema_capabilities = self.detect_schema_capabilities()
        self._ensure_compatibility_mode_supported()
        self._log_runtime_mode()
        self.reset_status()
        self._load_task_definitions()

        if self.cfg.check_configuration_interval > 0:
            self.th_check_configuration = PeriodicTask(
                interval=self.cfg.check_configuration_interval,
                task_function=self.config_tmgr_from_ddbb,
            )
            self.th_check_configuration.start()
            self.log.info(f"Check DDBB configuration each {self.cfg.check_configuration_interval}seconds")

    def _run_async(self, coroutine):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        raise RuntimeError("Use the async API when TMgr is called from an active event loop.")

    def _normalize_compatibility_mode(self, mode) -> str:
        normalized = str(mode or "AUTO").upper()
        if normalized not in {"AUTO", "LEGACY", "SAFE"}:
            return "AUTO"
        return normalized

    def _ensure_compatibility_mode_supported(self):
        mode = self._normalize_compatibility_mode(getattr(self.cfg, "compatibility_mode", "AUTO"))
        if mode == "SAFE" and not self.schema_capabilities.get("supports_lease_columns", False):
            raise RuntimeError(
                "SAFE compatibility mode requires the upgraded tmgr_tasks schema. "
                "Run the upgrade SQL script or set compatibility_mode to AUTO/LEGACY."
            )

    def _safe_mode_enabled(self) -> bool:
        mode = self._normalize_compatibility_mode(getattr(self.cfg, "compatibility_mode", "AUTO"))
        if mode == "LEGACY":
            return False
        if mode == "SAFE":
            return True
        return self.schema_capabilities.get("supports_lease_columns", False)

    def _log_runtime_mode(self):
        compat_mode = self._normalize_compatibility_mode(getattr(self.cfg, "compatibility_mode", "AUTO"))
        resolved_mode = "SAFE" if self._safe_mode_enabled() else "LEGACY"
        self.log.info(
            "Compatibility mode configured=%s resolved=%s supports_lease_columns=%s",
            compat_mode,
            resolved_mode,
            self.schema_capabilities.get("supports_lease_columns", False),
        )

    def _load_task_definitions(self):
        self.task_definitions = self.app_config.get("task_handlers", {})
        if self.task_definitions is not None:
            self.log.info(f"Task definitions loaded from config file: {len(self.task_definitions)}")

    def _resolve_task_filters(self):
        task_types = self.cfg.task_types
        filter_task_key = None
        if self.cfg.filter_task_key == FilterTaskKeyEnum.SELF_KEY:
            filter_task_key = self.cfg.taskmgr_name
        elif self.cfg.filter_task_key == FilterTaskKeyEnum.ANY_KEY:
            filter_task_key = None
        else:
            filter_task_key = self.cfg.filter_task_key
        return task_types, filter_task_key

    def _normalize_heartbeat_interval(self):
        lease_timeout = max(1, int(getattr(self.cfg, "lease_timeout_seconds", 300)))
        heartbeat_interval = max(1, int(getattr(self.cfg, "task_heartbeat_interval", 30)))
        if heartbeat_interval >= lease_timeout:
            heartbeat_interval = max(1, lease_timeout // 2)
        self.cfg.lease_timeout_seconds = lease_timeout
        self.cfg.task_heartbeat_interval = heartbeat_interval
        self.cfg.external_reconcile_interval_seconds = max(
            1,
            int(getattr(self.cfg, "external_reconcile_interval_seconds", 30)),
        )
        self.cfg.external_reconcile_batch_size = max(
            1,
            int(getattr(self.cfg, "external_reconcile_batch_size", 10)),
        )

    def stop_tasks(self):
        self.log.debug("Stop threads if needed.")
        if self.th_check_configuration:
            self.th_check_configuration.stop()

    def detect_schema_capabilities(self):
        return self._run_async(self.detect_schema_capabilities_async())

    async def detect_schema_capabilities_async(self):
        task_db = AsyncTaskDB()
        try:
            return await task_db.get_schema_capabilities()
        finally:
            await task_db.close_session()

    def config_tmgr_from_ddbb(self):
        return self._run_async(self.config_tmgr_from_ddbb_async())

    async def config_tmgr_from_ddbb_async(self):
        configuration_key = self.app_config["manager_name"]
        task_db = AsyncTaskDB()
        try:
            db_query_config = await task_db.get_task_mgr_configuration(configuration_key)
        finally:
            await task_db.close_session()

        if db_query_config is None:
            raise Exception(f"Configuration not exists, please check the configuration key {configuration_key} in DDBB.")

        cfg: Dict = db_query_config["config"]

        self.app_config["mgr_config"] = cfg
        self.cfg.task_types = cfg.get("task_types", [])
        self.cfg.filter_task_key = str(cfg.get("filter_task_key", FilterTaskKeyEnum.SELF_KEY)).upper()

        old_max_wait_count = self.cfg.max_wait_count
        old_check_configuration_interval = self.cfg.check_configuration_interval
        old_log_level = self.cfg.log_level

        self.cfg.max_wait_count = cfg.get("max_wait_count", 10)
        self.cfg.wait_between_tasks_seconds = cfg.get("wait_between_tasks_seconds", 1)
        self.cfg.monitor_wait_time_seconds = cfg.get("monitor_wait_time_seconds", -1)
        self.cfg.check_configuration_interval = cfg.get("check_configuration_interval", -1)
        self.cfg.log_level = cfg.get("log_level", logging.INFO)
        self.cfg.compatibility_mode = self._normalize_compatibility_mode(
            cfg.get("compatibility_mode", getattr(self.cfg, "compatibility_mode", "AUTO"))
        )
        self.cfg.lease_timeout_seconds = int(
            cfg.get("lease_timeout_seconds", getattr(self.cfg, "lease_timeout_seconds", 300))
        )
        self.cfg.task_heartbeat_interval = int(
            cfg.get("task_heartbeat_interval", getattr(self.cfg, "task_heartbeat_interval", 30))
        )
        self.cfg.external_reconcile_interval_seconds = int(
            cfg.get(
                "external_reconcile_interval_seconds",
                getattr(self.cfg, "external_reconcile_interval_seconds", 30),
            )
        )
        self.cfg.external_reconcile_batch_size = int(
            cfg.get(
                "external_reconcile_batch_size",
                getattr(self.cfg, "external_reconcile_batch_size", 10),
            )
        )
        self._normalize_heartbeat_interval()
        self.log.debug(f"Configuration loaded for {self.cfg.taskmgr_name}")

        if self.schema_capabilities.get("task_columns"):
            self._ensure_compatibility_mode_supported()

        if old_log_level != self.cfg.log_level:
            self.log.setLevel(level=self.cfg.log_level)
            self.log.info(f"Log new level set {self.cfg.taskmgr_name}")

        if old_max_wait_count != self.cfg.max_wait_count:
            with self.lock:
                self.max_wait_counter = 0
            if self.cfg.max_wait_count == -1:
                self.log.info("Task manager is in infinite mode.")

        if self.cfg.check_configuration_interval == 0 and self.cfg.check_configuration_interval != old_check_configuration_interval:
            self.log.info("Stop check DDBB")

    def reset_status(self):
        return self._run_async(self.reset_status_async())

    async def reset_status_async(self):
        task_types, filter_task_key = self._resolve_task_filters()
        _ = task_types
        task_db = AsyncTaskDB()
        try:
            await task_db.reset_status(
                filter_task_key=filter_task_key,
                supports_lease_columns=self._safe_mode_enabled(),
            )
        finally:
            await task_db.close_session()

    def get_task(self, id_task):
        return TaskDB().get_task(id_task)

    async def get_task_async(self, id_task):
        task_db = AsyncTaskDB()
        try:
            return await task_db.get_task(id_task)
        finally:
            await task_db.close_session()

    def fetch_pending_tasks(self):
        return self._run_async(self.fetch_pending_tasks_async())

    async def fetch_pending_tasks_async(self):
        task_types, filter_task_key = self._resolve_task_filters()
        task_db = AsyncTaskDB()
        try:
            return await task_db.get_pending_task(task_types=task_types, filter_task_key=filter_task_key)
        finally:
            await task_db.close_session()

    async def claim_next_task_async(self):
        task_types, filter_task_key = self._resolve_task_filters()
        task_db = AsyncTaskDB()
        try:
            if self._safe_mode_enabled():
                claim_token = uuid.uuid4().hex
                return await task_db.claim_pending_task(
                    task_types=task_types,
                    filter_task_key=filter_task_key,
                    claimed_by=self.manager_instance_id,
                    claim_token=claim_token,
                    lease_timeout_seconds=self.cfg.lease_timeout_seconds,
                )

            task = await task_db.get_pending_task(task_types=task_types, filter_task_key=filter_task_key)
            if not task:
                return None
            resp = await task_db.update_status(
                id=task["id"],
                new_status=TaskStatusEnum.CHECKING,
                prev_status=TaskStatusEnum.PENDING,
                progress=0,
                output="",
            )
            if resp["status"] == str(TaskStatusEnum.CHECKING):
                return task
            return None
        finally:
            await task_db.close_session()

    def task_definition_fetch(self, task_definition_type):
        return self._run_async(self.task_definition_fetch_async(task_definition_type=task_definition_type))

    async def task_definition_fetch_async(self, task_definition_type):
        search_type = self.mgr_config.get(LitEnum.task_definition_search_type, CFGOrderEnum.CFG_DB)
        task = None

        if search_type in [CFGOrderEnum.CFG_ONLY, CFGOrderEnum.CFG_DB]:
            task = self.task_definitions.get(task_definition_type)
            if task is None and search_type in [CFGOrderEnum.CFG_DB]:
                task_db = AsyncTaskDB()
                try:
                    task = await task_db.get_task_definition(task_type=task_definition_type)
                finally:
                    await task_db.close_session()
        elif search_type in [CFGOrderEnum.DB_ONLY, CFGOrderEnum.DB_CFG]:
            task_db = AsyncTaskDB()
            try:
                task = await task_db.get_task_definition(task_type=task_definition_type)
            finally:
                await task_db.close_session()
            if task is None and search_type in [CFGOrderEnum.DB_CFG]:
                task = self.task_definitions.get(task_definition_type)

        if not task:
            raise Exception(f"Task definition not found {task_definition_type}")

        if isinstance(task, dict):
            return task.get("config")
        return task["config"]

    def _extract_external_ref(self, task_ret: dict):
        if not isinstance(task_ret, dict):
            return None
        for key in ("external_ref", "container_id", "task_arn", "taskArn", "id"):
            value = task_ret.get(key)
            if value:
                return str(value)
        return None

    def _task_is_deferred(self, task_ret: dict) -> bool:
        if not isinstance(task_ret, dict):
            return False
        if task_ret.get("deferred"):
            return True
        return str(task_ret.get("status", "")).upper() in {"STARTED", "WAIT_EXECUTION"}

    def _task_is_terminal(self, task_ret: dict) -> bool:
        if not isinstance(task_ret, dict):
            return False
        if "terminal" in task_ret:
            return bool(task_ret.get("terminal"))
        return str(task_ret.get("status", "")).upper() in {"COMPLETED", "FINISHED", "ERROR"}

    async def _claim_external_task_for_reconciliation(self):
        task_types, filter_task_key = self._resolve_task_filters()
        task_db = AsyncTaskDB()
        try:
            return await task_db.claim_waiting_task_for_reconciliation(
                task_types=task_types,
                filter_task_key=filter_task_key,
                claimed_by=self.manager_instance_id,
                claim_token=uuid.uuid4().hex,
                lease_timeout_seconds=self.cfg.lease_timeout_seconds,
            )
        finally:
            await task_db.close_session()

    async def _reconcile_external_task_async(self, task_obj):
        task_id = str(task_obj["id"])
        task_type = str(task_obj["type"]).upper()
        claim_token = task_obj.get("claim_token")
        safe_mode = self._safe_mode_enabled()
        task_db = AsyncTaskDB()

        try:
            task_definition_cfg = await self.task_definition_fetch_async(task_definition_type=task_type)
            if "task_definition" not in task_definition_cfg or task_definition_cfg["task_definition"] is None:
                task_definition_cfg["task_definition"] = {}
            task_definition_cfg["task_definition"]["task_id_task"] = task_id
            task_definition_cfg["task_definition"]["external_ref"] = task_obj.get("external_ref")

            task_loader = TaskLoader(task_definition_cfg)
            task_ret = await task_loader.reconcile_task_async(
                task_definition=task_definition_cfg.get("task_definition"),
                external_ref=task_obj.get("external_ref"),
                task_record=task_obj,
            )

            if task_ret is None:
                await task_db.update_status(
                    id=task_id,
                    new_status=TaskStatusEnum.WAIT_EXECUTION,
                    output="Handler does not implement reconcile_task.",
                    release_claim=safe_mode,
                    claim_token=claim_token,
                    supports_lease_columns=safe_mode,
                    external_ref=task_obj.get("external_ref"),
                )
                return "SKIPPED"

            status = str(task_ret.get("status", "")).upper()
            message = task_ret.get("message")
            update_kwargs = {
                "progress": task_ret.get("progress", task_obj.get("progress", 0)),
                "external_ref": self._extract_external_ref(task_ret) or task_obj.get("external_ref"),
            }
            if safe_mode:
                update_kwargs["last_error"] = None if status not in {"ERROR"} else message

            if not self._task_is_terminal(task_ret):
                await task_db.update_status(
                    id=task_id,
                    new_status=TaskStatusEnum.WAIT_EXECUTION,
                    output=message,
                    release_claim=safe_mode,
                    claim_token=claim_token,
                    supports_lease_columns=safe_mode,
                    **update_kwargs,
                )
                return "RUNNING"

            if status in {"COMPLETED", "FINISHED"}:
                final_status = task_definition_cfg["task_handler"].get("task_next_status", TaskStatusEnum.FINISHED)
                await task_db.update_status(
                    id=task_id,
                    new_status=final_status,
                    output=message,
                    time_end="NOW()",
                    release_claim=safe_mode,
                    claim_token=claim_token,
                    supports_lease_columns=safe_mode,
                    **update_kwargs,
                )
                return "FINISHED"

            await task_db.update_status(
                id=task_id,
                new_status=TaskStatusEnum.ERROR,
                output=message,
                time_end="NOW()",
                release_claim=safe_mode,
                claim_token=claim_token,
                supports_lease_columns=safe_mode,
                **update_kwargs,
            )
            return "ERROR"
        except Exception as ex:
            msg = f"External reconciliation error: {str(ex)}"
            update_kwargs = {}
            if safe_mode:
                update_kwargs["last_error"] = msg
            await task_db.update_status(
                id=task_id,
                new_status=TaskStatusEnum.WAIT_EXECUTION,
                output=msg,
                release_claim=safe_mode,
                claim_token=claim_token,
                supports_lease_columns=safe_mode,
                external_ref=task_obj.get("external_ref"),
                **update_kwargs,
            )
            self.log.error("Task %s reconciliation failed: %s", task_id, msg)
            return "ERROR"
        finally:
            await task_db.close_session()

    async def reconcile_external_tasks_async(self):
        if not self._safe_mode_enabled():
            return 0

        reconciled = 0
        for _ in range(self.cfg.external_reconcile_batch_size):
            task_obj = await self._claim_external_task_for_reconciliation()
            if not task_obj:
                break
            await self._reconcile_external_task_async(task_obj)
            reconciled += 1
        return reconciled

    async def _maybe_reconcile_external_tasks(self):
        if not self._safe_mode_enabled():
            return 0

        now = asyncio.get_running_loop().time()
        if self.last_external_reconcile_at is None:
            self.last_external_reconcile_at = 0

        if now - self.last_external_reconcile_at < self.cfg.external_reconcile_interval_seconds:
            return 0

        reconciled = await self.reconcile_external_tasks_async()
        self.last_external_reconcile_at = now
        if reconciled:
            self.log.debug("Reconciled %s external task(s).", reconciled)
        return reconciled

    async def _run_task_with_heartbeat(self, task_loader: TaskLoader, task_id: str, claim_token: str | None):
        if not self._safe_mode_enabled() or not claim_token:
            return await task_loader.run_task_async()

        task_future = asyncio.create_task(task_loader.run_task_async())
        lease_db = AsyncTaskDB()
        try:
            while True:
                done, _ = await asyncio.wait({task_future}, timeout=self.cfg.task_heartbeat_interval)
                if task_future in done:
                    return task_future.result()
                await lease_db.touch_lease(
                    id_task=task_id,
                    claim_token=claim_token,
                    lease_timeout_seconds=self.cfg.lease_timeout_seconds,
                )
        finally:
            await lease_db.close_session()

    def execute_task(self, id_task):
        return self._run_async(self.execute_task_async(id_task=id_task))

    async def execute_task_async(self, id_task=None, claimed_task=None):
        log = logging.getLogger(__name__)
        task_ret = {}
        safe_mode = self._safe_mode_enabled()
        task_db = AsyncTaskDB()
        claim_token = None

        try:
            task_obj = claimed_task
            if task_obj is None:
                resp = await task_db.update_status(
                    id=id_task,
                    new_status=TaskStatusEnum.CHECKING,
                    prev_status=TaskStatusEnum.PENDING,
                    progress=0,
                    output="",
                )
                if resp["status"] != str(TaskStatusEnum.CHECKING):
                    log.warning(f"Task {id_task} not launched. Maybe was deleted or executed in other process.")
                    return {}
                task_obj = await task_db.get_task(id_task)
            else:
                id_task = str(task_obj["id"])
                claim_token = task_obj.get("claim_token")

            if task_obj is None:
                return {}

            log.info(f"Starting task execution: {id_task}")
            task_type = str(task_obj["type"]).upper()
            task_definition_cfg = await self.task_definition_fetch_async(task_definition_type=task_type)
            if task_definition_cfg is None:
                msg = f"task definition not found: {task_type}"
                update_kwargs = {"progress": 0}
                if safe_mode:
                    update_kwargs["last_error"] = msg
                await task_db.update_status(
                    id=id_task,
                    new_status=TaskStatusEnum.ERROR,
                    output=msg,
                    release_claim=safe_mode,
                    claim_token=claim_token,
                    supports_lease_columns=safe_mode,
                    **update_kwargs,
                )
                return {}

            launch_type = task_definition_cfg["task_handler"].get("launchType", "")
            if launch_type == "":
                launch_type = task_definition_cfg.get("launchType", "")
            launch_type = launch_type.upper()

            if "task_definition" not in task_definition_cfg or task_definition_cfg["task_definition"] is None:
                task_definition_cfg["task_definition"] = {}
            task_definition_cfg["task_definition"]["task_id_task"] = str(id_task)

            await task_db.update_status(
                id=id_task,
                new_status=TaskStatusEnum.CHECKING,
                output="",
                time_start="NOW()",
                claim_token=claim_token,
                supports_lease_columns=safe_mode,
            )

            tl = TaskLoader(task_definition_cfg)
            task_ret = await self._run_task_with_heartbeat(tl, str(id_task), claim_token)
            if not isinstance(task_ret, dict):
                task_ret = {}

            if str(task_ret.get("status", "")).upper() == "ERROR":
                msg = task_ret.get("message", "Unknown task handler error")
                update_kwargs = {"progress": 0}
                if safe_mode:
                    update_kwargs["last_error"] = msg
                await task_db.update_status(
                    id=id_task,
                    new_status=TaskStatusEnum.ERROR,
                    output=msg,
                    release_claim=safe_mode,
                    claim_token=claim_token,
                    supports_lease_columns=safe_mode,
                    **update_kwargs,
                )
                log.error(f"Task {task_type} {id_task} launched with errors: {msg}")
            else:
                log.debug(f"Task {task_type} {id_task} launchType:{launch_type}.")
                if launch_type == str(LitEnum.LAUNCHTYPE_INTERNAL) and not self._task_is_deferred(task_ret):
                    task_next_status = task_definition_cfg["task_handler"].get(
                        "task_next_status",
                        TaskStatusEnum.FINISHED,
                    )
                    msg = task_ret.get("message", None)
                    await task_db.update_status(
                        id=id_task,
                        new_status=task_next_status,
                        output=msg,
                        progress=task_ret.get("progress", 100),
                        time_end="NOW()",
                        release_claim=safe_mode,
                        claim_token=claim_token,
                        supports_lease_columns=safe_mode,
                    )
                else:
                    msg = task_ret.get("message", None)
                    update_kwargs = {
                        "progress": task_ret.get("progress", 0),
                    }
                    if safe_mode:
                        update_kwargs["external_ref"] = self._extract_external_ref(task_ret)
                        update_kwargs["last_error"] = None
                    await task_db.update_status(
                        id=id_task,
                        new_status=TaskStatusEnum.WAIT_EXECUTION,
                        output=msg,
                        release_claim=safe_mode,
                        claim_token=claim_token,
                        supports_lease_columns=safe_mode,
                        **update_kwargs,
                    )
                log.info(f"Task {id_task} finished.")

            task_ret["next_task_wait_seconds"] = task_definition_cfg.get("next_task_wait_seconds", 0)
            return task_ret
        except Exception as ex:
            msg = str(ex)
            self.log.error(f"Task {id_task} raised error {msg}")
            update_kwargs = {"progress": 0}
            if safe_mode:
                update_kwargs["last_error"] = msg
            try:
                await task_db.update_status(
                    id=id_task,
                    new_status=TaskStatusEnum.ERROR,
                    output=msg,
                    release_claim=safe_mode,
                    claim_token=claim_token,
                    supports_lease_columns=safe_mode,
                    **update_kwargs,
                )
            except Exception:
                self.log.exception("Unable to persist task error state.")
            return {
                "status": "ERROR",
                "message": msg,
                "next_task_wait_seconds": 0,
            }
        finally:
            await task_db.close_session()

    def monitor_and_execute(self):
        return self._run_async(self.monitor_and_execute_async())

    async def monitor_and_execute_async(self):
        try:
            self.max_wait_counter = 0
            while True:
                await self._maybe_reconcile_external_tasks()
                task = await self.claim_next_task_async()
                if task:
                    task_ret = await self.execute_task_async(claimed_task=task)
                    next_task_wait_seconds = task_ret.get("next_task_wait_seconds", 0)
                    if self.cfg.wait_between_tasks_seconds > 0 or next_task_wait_seconds > 0:
                        if next_task_wait_seconds > self.cfg.wait_between_tasks_seconds:
                            wait_between_tasks_seconds = next_task_wait_seconds
                        else:
                            wait_between_tasks_seconds = self.cfg.wait_between_tasks_seconds
                        await asyncio.sleep(wait_between_tasks_seconds)
                    self.max_wait_counter = 0
                else:
                    self.max_wait_counter += 1
                    if (
                        self.cfg.monitor_wait_time_seconds > 0
                        and self.max_wait_counter == self.cfg.max_wait_count
                    ):
                        self.log.info(
                            "No pending tasks stopping Task manager. Wait time was %s seconds between checks. "
                            "If you want to deactivate automatic close set max_wait_count=-1",
                            str(self.cfg.monitor_wait_time_seconds),
                        )
                        return
                if self.cfg.monitor_wait_time_seconds > 0:
                    await asyncio.sleep(self.cfg.monitor_wait_time_seconds)
        finally:
            self.stop_tasks()
