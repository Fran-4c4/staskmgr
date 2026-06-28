import json
import logging
import unittest
from unittest.mock import patch

from task_handlers.docker_task_handler import DockerTaskHandler
from task_handlers.ecs_task_handler import ECSTaskHandler
from tmgr.log_handlers.task_context import (
    JsonTaskLogFormatter,
    TaskContextFilter,
    TaskLogContext,
)
from tmgr.task_correlation import build_task_context


class FakeContainer:
    """Docker container double for handler unit tests."""

    id = "container-full-id"
    short_id = "short123"
    name = "task-task1234-260628000000"

    def remove(self, force=False):
        """Record remove calls without touching Docker."""

        self.removed = True
        self.force = force


class FakeDockerContainers:
    """Docker container collection double that records run kwargs."""

    def __init__(self):
        """Create an empty capture for Docker run kwargs."""

        self.run_kwargs = None

    def run(self, **kwargs):
        """Capture Docker run kwargs and return a fake container."""

        self.run_kwargs = kwargs
        return FakeContainer()


class FakeDockerClient:
    """Docker client double with container and network surfaces."""

    def __init__(self):
        """Create Docker SDK-like surfaces used by the handler."""

        self.containers = FakeDockerContainers()
        self.networks = {}
        self.closed = False

    def close(self):
        """Record client close calls."""

        self.closed = True


class FakeEcsClient:
    """ECS client double that records run_task kwargs."""

    def __init__(self):
        """Create an empty capture for ECS run_task kwargs."""

        self.run_task_kwargs = None

    def run_task(self, **kwargs):
        """Capture ECS run_task kwargs and return one task ARN."""

        self.run_task_kwargs = kwargs
        return {
            "failures": [],
            "tasks": [{"taskArn": "arn:aws:ecs:task/example/task-123"}],
        }


class TaskCorrelationTests(unittest.TestCase):
    """Unit tests for task correlation metadata and logging context."""

    def tearDown(self):
        """Clear task log context after each test."""

        TaskLogContext.clear_context()

    def test_build_task_context_is_best_effort(self):
        """Optional correlation fields should be omitted when absent."""

        context = build_task_context({"task_id_task": "task-123"})

        self.assertEqual(context, {"task_id": "task-123"})

    def test_json_formatter_emits_task_context(self):
        """JSON task formatter should include context fields when present."""

        token = TaskLogContext.set_context(task_id="task-123", parent_request_id="req-1")
        try:
            record = logging.LogRecord(
                name="tmgr.test",
                level=logging.INFO,
                pathname=__file__,
                lineno=1,
                msg="Task started",
                args=(),
                exc_info=None,
            )
            TaskContextFilter().filter(record)
            payload = json.loads(JsonTaskLogFormatter().format(record))
        finally:
            TaskLogContext.reset_context(token)

        self.assertEqual(payload["task_id"], "task-123")
        self.assertEqual(payload["parent_request_id"], "req-1")
        self.assertEqual(payload["message"], "Task started")

    def test_docker_handler_injects_environment_and_labels(self):
        """Docker handler should propagate available metadata best-effort."""

        fake_client = FakeDockerClient()
        task_definition = {
            "task_id_task": "task-123",
            "task_type": "EXAMPLE_TASK",
            "task_manager": "EXAMPLE_TASK_MANAGER",
            "parent_request_id": "req-1",
            "process_chain_id": "chain-1",
            "deployment_environment": "DEV",
            "image": "worker:latest",
            "command": ["--task-id", "<idtask>"],
            "environment": {"EXISTING": "1"},
            "container_remove": False,
        }

        with patch("task_handlers.docker_task_handler.docker.from_env", return_value=fake_client):
            result = DockerTaskHandler().run_task(task_definition=task_definition)

        run_kwargs = fake_client.containers.run_kwargs
        self.assertEqual(result["external_ref"], "container-full-id")
        self.assertEqual(run_kwargs["environment"]["TASK_ID"], "task-123")
        self.assertEqual(run_kwargs["environment"]["TMGR_TASK_ID"], "task-123")
        self.assertEqual(run_kwargs["environment"]["PARENT_REQUEST_ID"], "req-1")
        self.assertEqual(run_kwargs["labels"]["com.staskmgr.task_id"], "task-123")
        self.assertEqual(run_kwargs["labels"]["com.staskmgr.process_chain_id"], "chain-1")
        self.assertEqual(run_kwargs["command"], ["--task-id", "task-123"])

    def test_ecs_handler_injects_environment_tags_and_returns_external_ref(self):
        """ECS handler should propagate metadata and expose the task ARN."""

        fake_ecs = FakeEcsClient()
        task_definition = {
            "task_id_task": "task-123",
            "task_type": "EXAMPLE_TASK",
            "parent_request_id": "req-1",
            "deployment_environment": "DEV",
            "region": "eu-west-1",
            "subnets": ["subnet-1"],
            "security_groups": ["sg-1"],
            "cluster_name": "cluster",
            "task_definition": "worker-task",
            "task_container_name": "worker",
            "launchType": "FARGATE",
            "networkMode": "awsvpc",
            "command": ["--task-id", "<idtask>"],
        }

        with patch("task_handlers.ecs_task_handler.boto3.client", return_value=fake_ecs):
            result = ECSTaskHandler().run_task(task_definition=task_definition)

        run_kwargs = fake_ecs.run_task_kwargs
        container_override = run_kwargs["overrides"]["containerOverrides"][0]
        env_by_name = {item["name"]: item["value"] for item in container_override["environment"]}
        tags_by_name = {item["key"]: item["value"] for item in run_kwargs["tags"]}

        self.assertEqual(result["external_ref"], "arn:aws:ecs:task/example/task-123")
        self.assertEqual(container_override["command"], ["--task-id", "task-123"])
        self.assertEqual(env_by_name["TASK_ID"], "task-123")
        self.assertEqual(env_by_name["PARENT_REQUEST_ID"], "req-1")
        self.assertEqual(tags_by_name["staskmgr.task_id"], "task-123")


if __name__ == "__main__":
    unittest.main()
