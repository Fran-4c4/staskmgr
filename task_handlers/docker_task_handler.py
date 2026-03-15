import datetime
import logging
import os

from dotenv import dotenv_values

try:
    import docker
    from docker.errors import APIError, DockerException, ImageNotFound, NotFound
except ImportError as ex:
    raise ImportError(
        "'docker' is not installed. Install using 'pip install docker'."
    ) from ex

from tmgr.task_handler_interface import TaskHandlerInterface


class DockerTaskHandler(TaskHandlerInterface):
    """
    Handles execution of tasks as Docker containers.

    Supported execution modes:
    - DETACHED: default mode for heavy containers. Launch and return immediately.
    - BLOCKING: wait for the container to finish and resolve the STMGR task inline.
    """

    SUPPORTED_EXECUTION_MODES = {"DETACHED", "BLOCKING"}

    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.client = docker.from_env()
        self.task_data: dict = None
        self.id_task: str = None
        self.image: str = None
        self.name: str = None
        self.environment: dict = None
        self.volumes: dict = None
        self.command: str | list | None = None
        self.entrypoint = None
        self.networks: list = None
        self.restart_policy = None
        self.environment_files: list = None
        self.container_remove: bool = None
        self.wait_for_completion: bool = False
        self.execution_mode: str = "DETACHED"
        self.capture_logs: bool = False
        self.log_max_bytes: int = 65536
        self.wait_timeout_seconds: int | None = None

    def config(self):
        """Configure handler from task_definition."""
        if not self.task_data:
            raise ValueError("task_data has not been assigned for configuration")

        self.id_task = str(self.task_data["task_id_task"])
        self.image = self.task_data.get("image")
        if not self.image:
            raise ValueError("Docker image ('image') is required in task_data")

        self.name = self.task_data.get("name")
        self.environment = dict(self.task_data.get("environment", {}) or {})
        self.volumes = dict(self.task_data.get("volumes", {}) or {})
        self.environment_files = list(self.task_data.get("environment_files", []) or [])
        self.entrypoint = self.task_data.get("entrypoint")
        self.networks = list(self.task_data.get("networks", []) or [])
        self.restart_policy = self.task_data.get("restart_policy")

        wait_for_completion = bool(self.task_data.get("wait_for_completion", False))
        self.execution_mode = str(
            self.task_data.get("execution_mode") or ("BLOCKING" if wait_for_completion else "DETACHED")
        ).upper()
        if self.execution_mode not in self.SUPPORTED_EXECUTION_MODES:
            raise ValueError(
                f"execution_mode must be one of {sorted(self.SUPPORTED_EXECUTION_MODES)}. "
                f"Received: {self.execution_mode}"
            )
        self.wait_for_completion = self.execution_mode == "BLOCKING"

        default_container_remove = self.wait_for_completion
        self.container_remove = bool(self.task_data.get("container_remove", default_container_remove))
        self.capture_logs = bool(self.task_data.get("capture_logs", self.wait_for_completion))
        self.log_max_bytes = int(self.task_data.get("log_max_bytes", 65536) or 0)

        wait_timeout_seconds = self.task_data.get("wait_timeout_seconds")
        self.wait_timeout_seconds = int(wait_timeout_seconds) if wait_timeout_seconds else None

        self._load_environment_files()
        self.command = self._config_command()

    def _load_environment_files(self):
        for entry in self.environment_files:
            env_type: str = entry.get("type", "")
            if env_type.upper() != "LOCAL":
                continue

            host_path = entry.get("value")
            if host_path and os.path.isfile(host_path):
                env_vars = dotenv_values(host_path)
                self.environment.update(env_vars)
            else:
                self.log.warning(f"Environment file not found or inaccessible: {host_path}")

    def _config_command(self):
        """
        Configure the command by injecting the actual id_task.
        """
        command = self.task_data.get("command")
        if command is None:
            return None

        if isinstance(command, str):
            if "<idtask>" in command:
                return command.replace("<idtask>", self.id_task)
            return command

        if isinstance(command, list):
            command = list(command)
            if "--idtask" in command:
                idx = command.index("--idtask")
                if idx + 1 < len(command):
                    command[idx + 1] = self.id_task
                else:
                    command.append(self.id_task)
            return command

        raise ValueError("command must be a string, list or null")

    @staticmethod
    def generate_container_name(id_task):
        prefix = "task"
        uuid_part = id_task.replace("-", "")[:8]
        timestamp = datetime.datetime.now().strftime("%y%m%d%H%M%S")
        return f"{prefix}-{uuid_part}-{timestamp}"

    def _resolve_container_name(self):
        generated_name = self.generate_container_name(id_task=self.id_task)
        if not self.name:
            return generated_name

        if "<idtask>" in self.name:
            return self.name.replace("<idtask>", self.id_task)
        if "<timestamp>" in self.name:
            timestamp = datetime.datetime.now().strftime("%y%m%d%H%M%S")
            return self.name.replace("<timestamp>", timestamp)
        return f"{self.name}-{generated_name}"

    def _get_wait_status_code(self, exit_status):
        if isinstance(exit_status, dict):
            return int(exit_status.get("StatusCode", -1))
        return int(exit_status)

    def _collect_logs(self, container):
        if not self.capture_logs:
            return None

        logs = container.logs(stdout=True, stderr=True)
        if self.log_max_bytes > 0 and len(logs) > self.log_max_bytes:
            logs = logs[-self.log_max_bytes :]
        return logs.decode("utf-8", errors="replace")

    def _attach_additional_networks(self, container):
        if len(self.networks) <= 1:
            return

        for net in self.networks[1:]:
            try:
                network = self.client.networks.get(net)
                network.connect(container)
            except NotFound as ex:
                raise RuntimeError(f"Network not found: {net}") from ex
            except APIError as ex:
                raise RuntimeError(f"Unable to connect container to network {net}: {str(ex)}") from ex

    def _cleanup_failed_launch(self, container):
        if container is None:
            return
        try:
            container.remove(force=True)
        except Exception:
            self.log.warning("Failed to cleanup container after launch error.", exc_info=True)

    def _run_detached(self, container):
        self.log.info("Container %s started in detached mode", container.short_id)
        return {
            "status": "STARTED",
            "message": "Container launched in detached mode.",
            "deferred": True,
            "execution_mode": self.execution_mode,
            "container_id": container.id,
            "container_short_id": container.short_id,
            "container_name": container.name,
            "external_ref": container.id,
        }

    def reconcile_task(self, **kwargs):
        """
        Reconcile a deferred Docker task using the persisted external_ref.
        """
        task_definition = kwargs.get("task_definition")
        if task_definition is None:
            raise Exception("DockerTaskHandler: task_definition is None, check configuration.")

        task_record = kwargs.get("task_record") or {}
        self.task_data = task_definition
        self.config()

        external_ref = kwargs.get("external_ref") or task_record.get("external_ref") or self.task_data.get("external_ref")
        if not external_ref:
            raise Exception("DockerTaskHandler: external_ref is required for reconciliation.")

        try:
            container = self.client.containers.get(external_ref)
        except NotFound:
            return {
                "status": "ERROR",
                "terminal": True,
                "external_ref": external_ref,
                "message": "Container not found during reconciliation.",
            }

        container.reload()
        state = container.attrs.get("State", {})
        container_status = str(state.get("Status", "")).lower()
        exit_code = state.get("ExitCode")

        if container_status in {"created", "running", "restarting", "paused"}:
            return {
                "status": "RUNNING",
                "terminal": False,
                "deferred": True,
                "external_ref": container.id,
                "container_id": container.id,
                "container_short_id": container.short_id,
                "container_name": container.name,
                "message": f"Container status is {container_status}.",
            }

        logs = self._collect_logs(container)
        response = {
            "status": "COMPLETED" if int(exit_code or 0) == 0 else "ERROR",
            "terminal": True,
            "external_ref": container.id,
            "container_id": container.id,
            "container_short_id": container.short_id,
            "container_name": container.name,
            "exit_code": int(exit_code or 0),
        }
        if logs is not None:
            response["logs"] = logs

        if response["status"] == "ERROR":
            response["message"] = f"Container finished with state={container_status} exit_code={response['exit_code']}"
        else:
            response["message"] = f"Container finished with state={container_status}"

        if self.container_remove:
            try:
                container.remove()
                self.log.info("Container %s removed after reconciliation", container.short_id)
            except Exception:
                self.log.warning("Failed to remove container after reconciliation.", exc_info=True)

        return response

    def _run_blocking(self, container):
        wait_kwargs = {}
        if self.wait_timeout_seconds:
            wait_kwargs["timeout"] = self.wait_timeout_seconds

        exit_status = container.wait(**wait_kwargs)
        status_code = self._get_wait_status_code(exit_status)
        logs = self._collect_logs(container)

        self.log.info("Container %s finished with exit code %s", container.short_id, status_code)
        if logs:
            self.log.debug("Container logs:\n%s", logs)

        response = {
            "status": "COMPLETED" if status_code == 0 else "ERROR",
            "execution_mode": self.execution_mode,
            "exit_code": status_code,
            "container_id": container.id,
            "container_short_id": container.short_id,
            "container_name": container.name,
        }
        if logs is not None:
            response["logs"] = logs

        if status_code != 0:
            response["message"] = f"Container finished with exit code {status_code}"

        if self.container_remove:
            container.remove()
            self.log.info("Container %s removed after execution", container.short_id)

        return response

    def run_task(self, **kwargs):
        """
        Execute the Docker container task.

        `execution_mode` defaults to `DETACHED` for heavy containers.
        Use `BLOCKING` for lightweight containers when the caller wants to wait.
        """
        container = None
        try:
            task_definition = kwargs.get("task_definition")
            if task_definition is None:
                raise Exception("DockerTaskHandler: task_definition is None, check configuration.")

            self.task_data = task_definition
            self.config()

            self.log.info("Launching Docker container with image: %s mode=%s", self.image, self.execution_mode)
            container_name = self._resolve_container_name()

            container = self.client.containers.run(
                image=self.image,
                name=container_name,
                environment=self.environment,
                volumes=self.volumes,
                command=self.command,
                entrypoint=self.entrypoint,
                detach=True,
                network=self.networks[0] if self.networks else None,
                remove=(self.container_remove if self.execution_mode == "DETACHED" else False),
                restart_policy=self.restart_policy,
            )

            self._attach_additional_networks(container)

            if self.execution_mode == "BLOCKING":
                return self._run_blocking(container)
            return self._run_detached(container)

        except ImageNotFound as ex:
            msg = f"Docker image not found: {self.image}"
            self.log.error(msg)
            raise Exception(msg) from ex
        except DockerException as ex:
            self._cleanup_failed_launch(container)
            msg = f"Docker general error: {str(ex)}"
            self.log.error(msg)
            raise Exception(msg) from ex
        except Exception as ex:
            self._cleanup_failed_launch(container)
            msg = f"Unexpected error in Docker task execution: {str(ex)}"
            self.log.error(msg)
            raise Exception(msg) from ex
        finally:
            try:
                self.client.close()
            except Exception:
                self.log.debug("Failed to close docker client cleanly.", exc_info=True)
