"""Build structured Kubernetes troubleshooting prompts for the LLM.

The system prompt casts the model as a Senior Kubernetes SRE.
The user prompt packages all collected evidence in a structured format
so the model can correlate logs, events, pod state, and networking.
"""

from __future__ import annotations

import json

from app.models.investigation import InvestigationPayload

# ---------------------------------------------------------------------------
# System prompt — persona and output contract
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a Senior Kubernetes Site Reliability Engineer (SRE) with 10+ years of experience.

Your job is to analyze Kubernetes cluster evidence and diagnose production incidents.

You will receive structured evidence from a live cluster including:
- Pod statuses and unhealthy pod details
- Application logs from failing pods
- Kubernetes warning events
- Deployment health and replica counts
- Networking / service issues

## Your Task

Analyze the evidence and produce a precise, actionable diagnosis.

## Output Format

Respond with ONLY valid JSON matching this exact schema:

{
  "root_cause": "<1-2 sentence specific root cause statement>",
  "explanation": "<2-4 sentence explanation correlating the evidence — logs, events, pod state, deployments>",
  "fix": "<Concrete fix description in plain language — what to change and where>",
  "kubectl_commands": ["<command 1>", "<command 2>"],
  "prevention": "<1-2 sentence recommendation to prevent this class of failure>",
  "confidence": <integer 0-100>,
  "confidence_reasoning": "<1-2 sentence explanation for the confidence score>"
}

## Rules

- Be specific. Never give generic Kubernetes advice.
- Base your answer ONLY on the evidence provided.
- If evidence is ambiguous, say so in the explanation and lower the confidence.
- If the cluster looks healthy, set confidence to 100 and say so in root_cause.
- kubectl_commands should be runnable as-is (replace placeholder names where needed).
- If you cannot determine a root cause, explain what additional evidence is needed.
- Return ONLY the JSON object — no markdown, no preamble, no extra text.
"""


# ---------------------------------------------------------------------------
# Evidence formatters
# ---------------------------------------------------------------------------


def _format_pods(payload: InvestigationPayload) -> str:
    pods = payload.pods
    if pods.error:
        return f"[ERROR] Could not retrieve pods: {pods.error}"
    if pods.healthy:
        return f"All {pods.total_pods} pods are healthy."
    lines = [f"Total pods: {pods.total_pods}  |  Unhealthy: {len(pods.problematic_pods)}"]
    for pod in pods.problematic_pods:
        age = f"{pod.age_seconds}s old" if pod.age_seconds is not None else "unknown age"
        msg = f" — {pod.message}" if pod.message else ""
        lines.append(f"  - {pod.namespace}/{pod.name}  status={pod.status}  ({age}){msg}")
    return "\n".join(lines)


def _format_logs(payload: InvestigationPayload) -> str:
    logs = payload.logs
    if not logs.failed_pod_logs:
        return "No log snippets collected (no failed pods or logs unavailable)."
    parts: list[str] = []
    for snippet in logs.failed_pod_logs:
        header = f"--- Logs: {snippet.namespace}/{snippet.name} ---"
        if snippet.error:
            parts.append(f"{header}\n[ERROR fetching logs: {snippet.error}]")
        elif snippet.lines:
            parts.append(header + "\n" + "\n".join(snippet.lines))
        else:
            parts.append(f"{header}\n[No relevant log lines found]")
    return "\n\n".join(parts)


def _format_events(payload: InvestigationPayload) -> str:
    events = payload.events
    if events.error:
        return f"[ERROR] Could not retrieve events: {events.error}"
    if events.healthy or not events.findings:
        return "No warning events detected."
    lines = [f"Warning events ({len(events.findings)} found, sorted by frequency):"]
    for finding in events.findings:
        lines.append(
            f"  [{finding.count}x] {finding.reason}  "
            f"{finding.namespace}/{finding.object_kind}/{finding.object_name}  "
            f"— {finding.message[:200]}"
        )
    return "\n".join(lines)


def _format_deployments(payload: InvestigationPayload) -> str:
    deployments = payload.deployments
    if deployments.error:
        return f"[ERROR] Could not retrieve deployments: {deployments.error}"
    if deployments.healthy:
        return f"All {deployments.total_deployments} deployments are healthy."
    lines = [f"Total deployments: {deployments.total_deployments}  |  Unhealthy: {len(deployments.unhealthy_deployments)}"]
    for dep in deployments.unhealthy_deployments:
        lines.append(
            f"  - {dep.namespace}/{dep.name}  "
            f"desired={dep.desired_replicas}  "
            f"available={dep.available_replicas}  "
            f"unavailable={dep.unavailable_replicas}  "
            f"issue={dep.issue}"
        )
        if dep.conditions:
            for cond in dep.conditions:
                lines.append(f"      condition: {cond}")
    return "\n".join(lines)


def _format_network(payload: InvestigationPayload) -> str:
    network = payload.network
    if network.error:
        return f"[ERROR] Could not retrieve networking info: {network.error}"
    if network.healthy:
        return f"All {network.total_services} services are healthy."
    lines = [f"Total services: {network.total_services}  |  Issues: {len(network.issues)}"]
    for issue in network.issues:
        lines.append(f"  - {issue.namespace}/{issue.service}  issue={issue.issue}  details={issue.details}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def build_user_prompt(payload: InvestigationPayload) -> str:
    """Build the user message that packages all Kubernetes evidence."""
    return f"""## Kubernetes Cluster Evidence

### 1. Pod Status
{_format_pods(payload)}

### 2. Application Logs (from failing pods)
{_format_logs(payload)}

### 3. Kubernetes Warning Events
{_format_events(payload)}

### 4. Deployment Health
{_format_deployments(payload)}

### 5. Networking / Services
{_format_network(payload)}

---
Analyze the evidence above and return the JSON diagnosis.
"""


def is_cluster_healthy(payload: InvestigationPayload) -> bool:
    """Return True when every section reports healthy — no LLM call needed."""
    return (
        payload.pods.healthy
        and payload.events.healthy
        and payload.deployments.healthy
        and payload.network.healthy
        and not payload.logs.failed_pod_logs
    )
