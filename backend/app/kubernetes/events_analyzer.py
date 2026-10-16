"""Summarize Kubernetes warning events from kubectl."""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.kubernetes.kubectl_executor import kubectl_executor
from app.models.investigation import EventFinding, EventsInvestigation

WATCHED_REASONS = {
    "FailedScheduling",
    "BackOff",
    "FailedMount",
    "FailedPull",
    "ErrImagePull",
    "Unhealthy",
}


def _event_count(event: dict[str, Any]) -> int:
    return int(event.get("count") or event.get("series", {}).get("count") or 1)


def analyze_events(namespace: str | None = None) -> EventsInvestigation:
    result = kubectl_executor.get_json("events", namespace=namespace)
    if not result.success:
        logger.error("Event analysis failed: {}", result.error)
        return EventsInvestigation(healthy=False, error=result.error)

    items = (result.parsed_json or {}).get("items") or []
    findings: list[EventFinding] = []

    for event in items:
        reason = event.get("reason") or ""
        if reason not in WATCHED_REASONS:
            continue

        involved = event.get("involvedObject") or {}
        findings.append(
            EventFinding(
                reason=reason,
                namespace=event.get("metadata", {}).get("namespace")
                or involved.get("namespace")
                or "default",
                object_kind=involved.get("kind") or "Unknown",
                object_name=involved.get("name") or "unknown",
                count=_event_count(event),
                message=(event.get("message") or "")[:400],
            )
        )

    findings.sort(key=lambda item: item.count, reverse=True)
    logger.info("Event analysis complete: {} watched findings", len(findings))
    return EventsInvestigation(healthy=len(findings) == 0, findings=findings)
