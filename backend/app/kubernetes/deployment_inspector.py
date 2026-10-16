"""Inspect deployments for replica and rollout problems."""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.kubernetes.kubectl_executor import kubectl_executor
from app.models.investigation import DeploymentInvestigation, UnhealthyDeployment


def _condition_summaries(status: dict[str, Any]) -> list[str]:
    summaries: list[str] = []
    for condition in status.get("conditions") or []:
        cond_type = condition.get("type") or "Unknown"
        cond_status = condition.get("status") or "Unknown"
        reason = condition.get("reason") or ""
        message = condition.get("message") or ""
        summaries.append(
            f"{cond_type}={cond_status}"
            + (f" ({reason})" if reason else "")
            + (f": {message}" if message else "")
        )
    return summaries


def _deployment_issue(spec: dict[str, Any], status: dict[str, Any]) -> str | None:
    desired = int(spec.get("replicas") or 0)
    available = int(status.get("availableReplicas") or 0)
    unavailable = int(status.get("unavailableReplicas") or 0)
    updated = int(status.get("updatedReplicas") or 0)

    for condition in status.get("conditions") or []:
        if (
            condition.get("type") == "Progressing"
            and condition.get("status") == "False"
            and condition.get("reason") == "ProgressDeadlineExceeded"
        ):
            return "rollout failure: ProgressDeadlineExceeded"
        if condition.get("type") == "Available" and condition.get("status") == "False":
            return f"deployment not available: {condition.get('reason') or 'Available=False'}"
        if condition.get("type") == "ReplicaFailure" and condition.get("status") == "True":
            return f"replica failure: {condition.get('message') or 'ReplicaFailure'}"

    if unavailable > 0:
        return f"{unavailable} unavailable replica(s)"
    if desired > 0 and available < desired:
        return f"available replicas {available}/{desired}"
    if desired > 0 and updated < desired:
        return f"updated replicas {updated}/{desired}"
    return None


def inspect_deployments(namespace: str | None = None) -> DeploymentInvestigation:
    result = kubectl_executor.get_json("deployments", namespace=namespace)
    if not result.success:
        logger.error("Deployment inspection failed: {}", result.error)
        return DeploymentInvestigation(healthy=False, error=result.error)

    items = (result.parsed_json or {}).get("items") or []
    unhealthy: list[UnhealthyDeployment] = []

    for deployment in items:
        metadata = deployment.get("metadata") or {}
        spec = deployment.get("spec") or {}
        status = deployment.get("status") or {}
        issue = _deployment_issue(spec, status)
        if not issue:
            continue
        unhealthy.append(
            UnhealthyDeployment(
                name=metadata.get("name") or "unknown",
                namespace=metadata.get("namespace") or "default",
                desired_replicas=int(spec.get("replicas") or 0),
                available_replicas=int(status.get("availableReplicas") or 0),
                unavailable_replicas=int(status.get("unavailableReplicas") or 0),
                conditions=_condition_summaries(status),
                issue=issue,
            )
        )

    logger.info(
        "Deployment inspection complete: {} total, {} unhealthy",
        len(items),
        len(unhealthy),
    )
    return DeploymentInvestigation(
        healthy=len(unhealthy) == 0,
        unhealthy_deployments=unhealthy,
        total_deployments=len(items),
    )
