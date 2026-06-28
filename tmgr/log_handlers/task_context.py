"""Logging context helpers for tmgr task execution."""

from __future__ import annotations

import contextvars
import json
import logging
from datetime import datetime, timezone
from typing import Any

from tmgr.task_correlation import CONTEXT_FIELDS, build_task_context


_TASK_LOG_CONTEXT: contextvars.ContextVar[dict[str, str]] = contextvars.ContextVar(
    "tmgr_task_log_context",
    default={},
)


def _json_safe(value: Any) -> Any:
    """Return a JSON-serializable representation for log payloads."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


class TaskLogContext:
    """Process-local task correlation context backed by contextvars."""

    @classmethod
    def set_context(cls, **context: Any) -> contextvars.Token:
        """Set the current task logging context and return its reset token."""

        clean_context = {
            field_name: str(value)
            for field_name, value in context.items()
            if field_name in CONTEXT_FIELDS and value not in (None, "")
        }
        return _TASK_LOG_CONTEXT.set(clean_context)

    @classmethod
    def set_from_task(
        cls,
        task_definition: dict[str, Any] | None = None,
        task_record: Any = None,
        environment: dict[str, Any] | None = None,
    ) -> contextvars.Token:
        """Set context by extracting metadata from task runtime sources."""

        return cls.set_context(
            **build_task_context(
                task_definition=task_definition,
                task_record=task_record,
                environment=environment,
            )
        )

    @classmethod
    def get_context(cls) -> dict[str, str]:
        """Return a copy of the current task logging context."""

        return dict(_TASK_LOG_CONTEXT.get() or {})

    @classmethod
    def reset_context(cls, token: contextvars.Token) -> None:
        """Reset the task logging context using a previous token."""

        _TASK_LOG_CONTEXT.reset(token)

    @classmethod
    def clear_context(cls) -> contextvars.Token:
        """Clear the current task logging context and return its reset token."""

        return _TASK_LOG_CONTEXT.set({})


class TaskContextFilter(logging.Filter):
    """Attach task correlation fields from ``TaskLogContext`` to records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Populate missing task fields on one log record."""

        context = TaskLogContext.get_context()
        for field_name in CONTEXT_FIELDS:
            if not hasattr(record, field_name):
                setattr(record, field_name, context.get(field_name))
        return True


class JsonTaskLogFormatter(logging.Formatter):
    """Format log records as JSON lines with optional task context."""

    def format(self, record: logging.LogRecord) -> str:
        """Format one log record as a JSON object string."""

        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "severity": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field_name in CONTEXT_FIELDS:
            value = getattr(record, field_name, None)
            if value not in (None, ""):
                payload[field_name] = _json_safe(value)

        if isinstance(record.exc_info, tuple):
            payload["exception_type"] = getattr(record.exc_info[0], "__name__", "Exception")
            payload["exception_stacktrace"] = self.formatException(record.exc_info)

        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(payload, ensure_ascii=True, default=str)


def attach_task_context_filter(logger: logging.Logger | None = None) -> TaskContextFilter:
    """Attach one task context filter to every current handler."""

    target_logger = logger or logging.getLogger()
    existing_filter: TaskContextFilter | None = None
    for handler in target_logger.handlers:
        for item in handler.filters:
            if isinstance(item, TaskContextFilter):
                existing_filter = item
                break
        if existing_filter is not None:
            break

    task_filter = existing_filter or TaskContextFilter()
    for handler in target_logger.handlers:
        if not any(isinstance(item, TaskContextFilter) for item in handler.filters):
            handler.addFilter(task_filter)
    return task_filter
