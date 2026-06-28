"""Task correlation helpers for runtime metadata propagation."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any


CONTEXT_FIELDS = (
    "task_id",
    "task_type",
    "task_manager",
    "parent_request_id",
    "process_chain_id",
    "container_id",
    "container_name",
    "service_name",
    "deployment_environment",
)

ENV_FIELD_NAMES = {
    "task_id": "TASK_ID",
    "task_type": "TASK_TYPE",
    "task_manager": "TASK_MANAGER",
    "parent_request_id": "PARENT_REQUEST_ID",
    "process_chain_id": "PROCESS_CHAIN_ID",
    "container_id": "CONTAINER_ID",
    "container_name": "CONTAINER_NAME",
    "service_name": "SERVICE_NAME",
    "deployment_environment": "DEPLOYMENT_ENVIRONMENT",
}

DOCKER_LABEL_NAMES = {
    "task_id": "com.staskmgr.task_id",
    "task_type": "com.staskmgr.task_type",
    "task_manager": "com.staskmgr.task_manager",
    "parent_request_id": "com.staskmgr.parent_request_id",
    "process_chain_id": "com.staskmgr.process_chain_id",
    "service_name": "com.staskmgr.service",
    "deployment_environment": "com.staskmgr.environment",
}

ECS_TAG_NAMES = {
    "task_id": "staskmgr.task_id",
    "task_type": "staskmgr.task_type",
    "task_manager": "staskmgr.task_manager",
    "parent_request_id": "staskmgr.parent_request_id",
    "process_chain_id": "staskmgr.process_chain_id",
    "service_name": "staskmgr.service",
    "deployment_environment": "staskmgr.environment",
}


def _get_value(source: Any, *keys: str) -> Any:
    """Read the first present key from a mapping or object."""

    if source is None:
        return None
    for key in keys:
        if isinstance(source, Mapping):
            value = source.get(key)
        else:
            value = getattr(source, key, None)
        if value not in (None, ""):
            return value
    return None


def _as_mapping(value: Any) -> Mapping[str, Any]:
    """Return a mapping-like value or an empty mapping."""

    if isinstance(value, Mapping):
        return value
    return {}


def _clean_context(context: Mapping[str, Any]) -> dict[str, str]:
    """Normalize correlation values to non-empty strings."""

    clean: dict[str, str] = {}
    for field_name in CONTEXT_FIELDS:
        value = context.get(field_name)
        if value not in (None, ""):
            clean[field_name] = str(value)
    return clean


def build_task_context(
    task_definition: Mapping[str, Any] | None = None,
    task_record: Any = None,
    environment: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """Build best-effort task correlation metadata.

    Args:
        task_definition: Handler payload, usually
            ``tmgr_task_definitions.config.task_definition``.
        task_record: Optional ``tmgr_tasks`` row or mapping.
        environment: Optional environment mapping. Defaults to ``os.environ``.

    Returns:
        dict[str, str]: Context fields found in the available sources. Missing
        optional values are omitted so legacy task definitions keep working.
    """

    task_definition = _as_mapping(task_definition)
    parameters = _as_mapping(
        _get_value(task_definition, "parameters")
        or _get_value(task_record, "parameters")
    )
    environment = environment if environment is not None else os.environ

    context = {
        "task_id": (
            _get_value(task_definition, "task_id", "task_id_task", "id_task", "id")
            or _get_value(task_record, "id", "task_id")
            or _get_value(environment, "TASK_ID", "TMGR_TASK_ID")
        ),
        "task_type": (
            _get_value(task_definition, "task_type", "type")
            or _get_value(task_record, "type")
            or _get_value(environment, "TASK_TYPE")
        ),
        "task_manager": (
            _get_value(task_definition, "task_manager", "id_tmgr")
            or _get_value(task_record, "id_tmgr", "task_manager")
            or _get_value(environment, "TASK_MANAGER")
        ),
        "parent_request_id": (
            _get_value(task_definition, "parent_request_id", "request_id")
            or _get_value(parameters, "parent_request_id", "request_id")
            or _get_value(environment, "PARENT_REQUEST_ID")
        ),
        "process_chain_id": (
            _get_value(task_definition, "process_chain_id")
            or _get_value(parameters, "process_chain_id")
            or _get_value(environment, "PROCESS_CHAIN_ID")
        ),
        "container_id": (
            _get_value(task_definition, "container_id", "external_ref")
            or _get_value(task_record, "external_ref")
            or _get_value(environment, "CONTAINER_ID")
        ),
        "container_name": (
            _get_value(task_definition, "container_name")
            or _get_value(environment, "CONTAINER_NAME")
        ),
        "service_name": (
            _get_value(task_definition, "service_name")
            or _get_value(environment, "SERVICE_NAME")
        ),
        "deployment_environment": (
            _get_value(task_definition, "deployment_environment", "environment")
            or _get_value(environment, "DEPLOYMENT_ENVIRONMENT", "ENVIRONMENT")
        ),
    }
    return _clean_context(context)


def build_task_environment(
    base_environment: Mapping[str, Any] | None,
    context: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge best-effort task metadata into one environment mapping."""

    environment = dict(base_environment or {})
    clean_context = _clean_context(context)
    for field_name, env_name in ENV_FIELD_NAMES.items():
        value = clean_context.get(field_name)
        if value not in (None, ""):
            environment[env_name] = value

    task_id = clean_context.get("task_id")
    if task_id:
        environment.setdefault("TMGR_TASK_ID", task_id)
    return environment


def build_docker_labels(
    base_labels: Mapping[str, Any] | None,
    context: Mapping[str, Any],
) -> dict[str, str]:
    """Merge best-effort task metadata into Docker labels."""

    labels = {str(key): str(value) for key, value in dict(base_labels or {}).items()}
    clean_context = _clean_context(context)
    for field_name, label_name in DOCKER_LABEL_NAMES.items():
        value = clean_context.get(field_name)
        if value not in (None, ""):
            labels[label_name] = value
    return labels


def build_ecs_environment_overrides(context: Mapping[str, Any]) -> list[dict[str, str]]:
    """Build ECS container environment override entries."""

    clean_context = _clean_context(context)
    overrides: list[dict[str, str]] = []
    for field_name, env_name in ENV_FIELD_NAMES.items():
        value = clean_context.get(field_name)
        if value not in (None, ""):
            overrides.append({"name": env_name, "value": value})
    return overrides


def build_ecs_tags(context: Mapping[str, Any]) -> list[dict[str, str]]:
    """Build ECS task tags from available correlation metadata."""

    clean_context = _clean_context(context)
    tags: list[dict[str, str]] = []
    for field_name, tag_name in ECS_TAG_NAMES.items():
        value = clean_context.get(field_name)
        if value not in (None, ""):
            tags.append({"key": tag_name, "value": value})
    return tags
