"""Orchestrate Kubernetes evidence collection and AI reasoning."""

from loguru import logger

from app.ai.agent import run_agent
from app.kubernetes.deployment_inspector import inspect_deployments
from app.kubernetes.events_analyzer import analyze_events
from app.kubernetes.logs_collector import collect_logs
from app.kubernetes.network_inspector import inspect_network
from app.kubernetes.pod_inspector import inspect_pods, list_pod_snapshots
from app.kubernetes.kubectl_executor import kubectl_executor
from app.models.investigation import (
    DeploymentInvestigation,
    EventsInvestigation,
    InvestigationPayload,
    InvestigationResponse,
    NetworkInvestigation,
)


from app.services.realtime import publish_progress


def investigate_cluster(
    channel: str = "investigations",
    context: str | None = None,
    namespace: str | None = None,
    pod_name: str | None = None,
) -> InvestigationResponse:
    # ── 0. Set target cluster context ───────────────────────────────────────
    kubectl_executor.set_context(context)
    if context:
        logger.info("Investigating cluster context: {}", context)

    # ── 1. Collect Kubernetes evidence ──────────────────────────────────────
    logger.info("Starting Kubernetes investigation")

    publish_progress(step="checking_pods", message="Checking Pods", status="running", channel=channel)
    pods = inspect_pods(namespace=namespace)
    if pod_name:
        pods.problematic_pods = [pod for pod in pods.problematic_pods if pod.name == pod_name]
        pods.total_pods = len(pods.problematic_pods)
        pods.healthy = len(pods.problematic_pods) == 0
    publish_progress(step="checking_pods", message="Checking Pods", status="done", channel=channel)

    publish_progress(step="reading_logs", message="Reading Logs", status="running", channel=channel)
    logs = collect_logs(pods.problematic_pods)
    publish_progress(step="reading_logs", message="Reading Logs", status="done", channel=channel)

    publish_progress(step="analyzing_events", message="Analyzing Events", status="running", channel=channel)
    events = analyze_events(namespace=namespace)
    if pod_name:
        events.findings = [finding for finding in events.findings if finding.object_name == pod_name]
        events.healthy = len(events.findings) == 0
    publish_progress(step="analyzing_events", message="Analyzing Events", status="done", channel=channel)

    publish_progress(step="inspecting_deployments", message="Inspecting Deployments", status="running", channel=channel)
    deployments = inspect_deployments(namespace=namespace)
    if pod_name:
        # A pod-targeted investigation should not be influenced by other deployments.
        deployments = DeploymentInvestigation(healthy=True, total_deployments=0)
    publish_progress(step="inspecting_deployments", message="Inspecting Deployments", status="done", channel=channel)

    publish_progress(step="checking_networking", message="Checking Networking", status="running", channel=channel)
    pod_items, pods_list_error = list_pod_snapshots(namespace=namespace)
    network = inspect_network(pod_items, namespace=namespace)
    if pod_name:
        # Service health is not relevant to a specific pod startup failure.
        network = NetworkInvestigation(healthy=True, total_services=0)
    if pods_list_error and network.error is None:
        network.error = pods_list_error
    publish_progress(step="checking_networking", message="Checking Networking", status="done", channel=channel)

    investigation = InvestigationPayload(
        pods=pods,
        logs=logs,
        events=events,
        deployments=deployments,
        network=network,
    )

    kubectl_errors = [
        section.error
        for section in (pods, logs, events, deployments, network)
        if section.error
    ]
    status = "error" if kubectl_errors and pods.total_pods == 0 and pods.error else "success"
    message = None
    if status == "error":
        message = pods.error or "kubectl investigation failed"

    logger.info("Kubernetes investigation finished with status={}", status)

    # ── 2. Check if cluster is healthy (no issues found) ────────────────────
    cluster_healthy = (
        status != "error"
        and pods.healthy
        and events.healthy
        and deployments.healthy
        and network.healthy
    )

    # ── 3. AI reasoning ─────────────────────────────────────────────────────
    diagnosis = None
    if status != "error" and not cluster_healthy:
        publish_progress(step="ai_reasoning", message="AI Reasoning", status="running", channel=channel)
        logger.info("Running AI Kubernetes agent")
        diagnosis = run_agent(investigation)
        publish_progress(
            step="ai_reasoning",
            message="AI Reasoning",
            status="done",
            channel=channel,
        )
        publish_progress(
            step="root_cause_found",
            message="Root Cause Found",
            status="done",
            channel=channel,
            meta={"root_cause": diagnosis.root_cause if diagnosis else "No issue found"},
        )
    elif cluster_healthy:
        publish_progress(
            step="ai_reasoning",
            message="Cluster Healthy",
            status="done",
            channel=channel,
        )
        publish_progress(
            step="root_cause_found",
            message="No Issues Detected",
            status="done",
            channel=channel,
            meta={"root_cause": "Cluster appears healthy"},
        )
        message = "healthy"

    return InvestigationResponse(
        status=status,
        investigation=investigation,
        diagnosis=diagnosis,
        message=message,
    )
