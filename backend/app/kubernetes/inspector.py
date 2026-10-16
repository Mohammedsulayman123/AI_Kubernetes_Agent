"""Compatibility wrappers for Kubernetes inspectors."""

from app.kubernetes.deployment_inspector import inspect_deployments
from app.kubernetes.events_analyzer import analyze_events
from app.kubernetes.pod_inspector import inspect_pods


def inspect_nodes() -> None:
    pass


def inspect_events():
    return analyze_events()


__all__ = [
    "inspect_pods",
    "inspect_nodes",
    "inspect_events",
    "inspect_deployments",
]
