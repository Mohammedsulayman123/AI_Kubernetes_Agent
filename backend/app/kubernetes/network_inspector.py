"""Inspect services, selectors, endpoints, and DNS-related clues."""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.kubernetes.kubectl_executor import kubectl_executor
from app.models.investigation import NetworkInvestigation, NetworkIssue


def _labels_match(selector: dict[str, str], labels: dict[str, str]) -> bool:
    return all(labels.get(key) == value for key, value in selector.items())


def _endpoint_ready_count(endpoint: dict[str, Any]) -> int:
    ready = 0
    for subset in endpoint.get("subsets") or []:
        ready += len(subset.get("addresses") or [])
    return ready


def _dns_issues_from_pods(pods: list[dict[str, Any]]) -> list[NetworkIssue]:
    issues: list[NetworkIssue] = []
    for pod in pods:
        metadata = pod.get("metadata") or {}
        labels = metadata.get("labels") or {}
        name = metadata.get("name") or ""
        namespace = metadata.get("namespace") or "kube-system"
        is_dns = (
            labels.get("k8s-app") in {"kube-dns", "coredns"}
            or "coredns" in name
            or "kube-dns" in name
        )
        if not is_dns:
            continue
        phase = (pod.get("status") or {}).get("phase")
        if phase != "Running":
            issues.append(
                NetworkIssue(
                    service=name,
                    namespace=namespace,
                    issue="DNS-related pod not Running",
                    details=f"CoreDNS/kube-dns pod phase is {phase}",
                )
            )
    return issues


def inspect_network(
    pod_items: list[dict[str, Any]] | None = None, namespace: str | None = None
) -> NetworkInvestigation:
    services_result = kubectl_executor.get_json("svc", namespace=namespace)
    if not services_result.success:
        logger.error("Network inspection failed on services: {}", services_result.error)
        return NetworkInvestigation(healthy=False, error=services_result.error)

    endpoints_result = kubectl_executor.get_json("endpoints", namespace=namespace)
    endpoints_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    endpoints_error: str | None = None
    if not endpoints_result.success:
        endpoints_error = endpoints_result.error
        logger.warning("Could not list endpoints: {}", endpoints_error)
    else:
        for endpoint in (endpoints_result.parsed_json or {}).get("items") or []:
            metadata = endpoint.get("metadata") or {}
            key = (metadata.get("namespace") or "default", metadata.get("name") or "")
            endpoints_by_key[key] = endpoint

    pods = pod_items if pod_items is not None else []
    service_items = (services_result.parsed_json or {}).get("items") or []
    issues: list[NetworkIssue] = []

    for service in service_items:
        metadata = service.get("metadata") or {}
        spec = service.get("spec") or {}
        name = metadata.get("name") or "unknown"
        namespace = metadata.get("namespace") or "default"
        selector = spec.get("selector") or {}
        svc_type = spec.get("type") or "ClusterIP"

        if name == "kubernetes" and namespace == "default":
            continue

        if not selector:
            if svc_type != "ExternalName":
                issues.append(
                    NetworkIssue(
                        service=name,
                        namespace=namespace,
                        issue="missing selector",
                        details="Service has no pod selector; traffic may not reach pods",
                    )
                )
            continue

        matching_pods = [
            pod
            for pod in pods
            if (pod.get("metadata") or {}).get("namespace") == namespace
            and _labels_match(selector, (pod.get("metadata") or {}).get("labels") or {})
        ]
        if not matching_pods:
            issues.append(
                NetworkIssue(
                    service=name,
                    namespace=namespace,
                    issue="selector mismatch",
                    details=f"No pods match selector {selector}",
                )
            )
            continue

        endpoint = endpoints_by_key.get((namespace, name))
        if endpoints_error:
            continue
        if endpoint is None or _endpoint_ready_count(endpoint) == 0:
            issues.append(
                NetworkIssue(
                    service=name,
                    namespace=namespace,
                    issue="missing endpoints",
                    details="Service has matching selector but no ready endpoints",
                )
            )

    issues.extend(_dns_issues_from_pods(pods))

    error = endpoints_error
    logger.info(
        "Network inspection complete: {} services, {} issues",
        len(service_items),
        len(issues),
    )
    return NetworkInvestigation(
        healthy=len(issues) == 0 and error is None,
        issues=issues,
        total_services=len(service_items),
        error=error,
    )
