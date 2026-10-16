"""Inspect pods and flag unhealthy ones from kubectl JSON."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from loguru import logger

from app.kubernetes.kubectl_executor import kubectl_executor
from app.models.investigation import PodInvestigation, ProblematicPod

UNHEALTHY_WAITING = {
    "CrashLoopBackOff",
    "ImagePullBackOff",
    "ErrImagePull",
    "CreateContainerError",
    "CreateContainerConfigError",
    "InvalidImageName",
    "Error",
    "RunContainerError",
}
UNHEALTHY_TERMINATED = {"OOMKilled", "Error", "StartError", "ContainerCannotRun"}
STUCK_WAITING = {"ContainerCreating", "PodInitializing"}
STUCK_AFTER_SECONDS = 120


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _age_seconds(pod: dict[str, Any]) -> int | None:
    created = _parse_timestamp(pod.get("metadata", {}).get("creationTimestamp"))
    if created is None:
        return None
    now = datetime.now(timezone.utc)
    return max(0, int((now - created).total_seconds()))


def _container_states(pod: dict[str, Any]) -> list[dict[str, Any]]:
    status = pod.get("status") or {}
    states: list[dict[str, Any]] = []
    for key in ("containerStatuses", "initContainerStatuses"):
        for container in status.get(key) or []:
            states.append(container)
    return states


def _problem_from_pod(pod: dict[str, Any]) -> ProblematicPod | None:
    metadata = pod.get("metadata") or {}
    status = pod.get("status") or {}
    name = metadata.get("name") or "unknown"
    namespace = metadata.get("namespace") or "default"
    phase = status.get("phase") or "Unknown"
    age = _age_seconds(pod)
    reason = status.get("reason")
    message = status.get("message")

    for container in _container_states(pod):
        waiting = (container.get("state") or {}).get("waiting") or {}
        terminated = (container.get("state") or {}).get("terminated") or {}
        last_terminated = (container.get("lastState") or {}).get("terminated") or {}

        waiting_reason = waiting.get("reason")
        if waiting_reason in UNHEALTHY_WAITING:
            return ProblematicPod(
                name=name,
                namespace=namespace,
                status=waiting_reason,
                message=waiting.get("message") or message,
                age_seconds=age,
            )

        if waiting_reason in STUCK_WAITING and (age or 0) >= STUCK_AFTER_SECONDS:
            return ProblematicPod(
                name=name,
                namespace=namespace,
                status=waiting_reason,
                message=waiting.get("message") or "container appears stuck",
                age_seconds=age,
            )

        terminated_reason = terminated.get("reason") or last_terminated.get("reason")
        if terminated_reason in UNHEALTHY_TERMINATED:
            return ProblematicPod(
                name=name,
                namespace=namespace,
                status=terminated_reason,
                message=terminated.get("message") or last_terminated.get("message") or message,
                age_seconds=age,
            )

        if (container.get("restartCount") or 0) >= 3 and waiting_reason:
            return ProblematicPod(
                name=name,
                namespace=namespace,
                status=waiting_reason,
                message=waiting.get("message") or f"restartCount={container.get('restartCount')}",
                age_seconds=age,
            )

    if phase in {"Failed", "Unknown"}:
        return ProblematicPod(
            name=name,
            namespace=namespace,
            status=reason or phase,
            message=message,
            age_seconds=age,
        )

    if phase == "Pending":
        for condition in status.get("conditions") or []:
            if condition.get("type") == "PodScheduled" and condition.get("status") == "False":
                cond_reason = condition.get("reason")
                if cond_reason in {"Unschedulable", "FailedScheduling"}:
                    return ProblematicPod(
                        name=name,
                        namespace=namespace,
                        status="Pending",
                        message=condition.get("message") or cond_reason,
                        age_seconds=age,
                    )

        if (age or 0) >= STUCK_AFTER_SECONDS:
            return ProblematicPod(
                name=name,
                namespace=namespace,
                status="Pending",
                message=message or "pod has been Pending too long",
                age_seconds=age,
            )

    return None


def inspect_pods(namespace: str | None = None) -> PodInvestigation:
    result = kubectl_executor.get_json("pods", namespace=namespace)
    if not result.success:
        logger.error("Pod inspection failed: {}", result.error)
        return PodInvestigation(healthy=False, error=result.error)

    items = (result.parsed_json or {}).get("items") or []
    problematic: list[ProblematicPod] = []
    for pod in items:
        problem = _problem_from_pod(pod)
        if problem:
            problematic.append(problem)

    logger.info(
        "Pod inspection complete: {} total, {} problematic",
        len(items),
        len(problematic),
    )
    return PodInvestigation(
        healthy=len(problematic) == 0,
        problematic_pods=problematic,
        total_pods=len(items),
    )


def list_pod_snapshots(namespace: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
    """Return raw pod items for other inspectors (selectors, DNS checks)."""
    result = kubectl_executor.get_json("pods", namespace=namespace)
    if not result.success:
        return [], result.error
    return (result.parsed_json or {}).get("items") or [], None
