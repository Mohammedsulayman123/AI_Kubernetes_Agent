"""Collect concise logs from failed pods."""

from __future__ import annotations

import re

from loguru import logger

from app.kubernetes.kubectl_executor import kubectl_executor
from app.models.investigation import LogsInvestigation, PodLogSnippet, ProblematicPod

RESOURCE_NAME_PATTERN = re.compile(r"^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$")
MAX_LOG_LINES = 40
TAIL_LINES = 80
FAILURE_HINTS = (
    "exception",
    "traceback",
    "error",
    "fail",
    "fatal",
    "panic",
    "oom",
    "killed",
    "connection refused",
    "connection reset",
    "refused",
    "timeout",
    "timed out",
    "unable to",
    "cannot",
    "missing",
    "required",
    "environment",
    "env var",
    "image",
    "pull",
    "unauthorized",
    "denied",
    "startup",
    "crash",
    "crashloop",
    "back-off",
    "exit code",
)


def _is_safe_name(value: str) -> bool:
    return bool(value) and len(value) <= 253 and bool(RESOURCE_NAME_PATTERN.fullmatch(value))


def _relevant_lines(raw_logs: str) -> list[str]:
    lines = [line.rstrip() for line in raw_logs.splitlines() if line.strip()]
    matched = [
        line
        for line in lines
        if any(hint in line.lower() for hint in FAILURE_HINTS)
    ]
    selected = matched[-MAX_LOG_LINES:] if matched else lines[-MAX_LOG_LINES:]
    return selected


def _fetch_logs(namespace: str, name: str, previous: bool = False) -> tuple[str, str | None]:
    args = [
        "logs",
        name,
        "-n",
        namespace,
        f"--tail={TAIL_LINES}",
        "--all-containers=true",
        "--request-timeout=20s",
    ]
    if previous:
        args.append("--previous")
    result = kubectl_executor.run(args, timeout=40)
    if not result.success:
        return "", result.error
    return result.stdout, None


def collect_logs(problematic_pods: list[ProblematicPod]) -> LogsInvestigation:
    snippets: list[PodLogSnippet] = []

    if not problematic_pods:
        logger.info("No problematic pods; skipping log collection")
        return LogsInvestigation(failed_pod_logs=[])

    for pod in problematic_pods:
        if not _is_safe_name(pod.name) or not _is_safe_name(pod.namespace):
            snippets.append(
                PodLogSnippet(
                    name=pod.name,
                    namespace=pod.namespace,
                    error="skipped unsafe pod or namespace name",
                )
            )
            continue

        stdout, error = _fetch_logs(pod.namespace, pod.name)
        previous_stdout = ""
        if pod.status in {"CrashLoopBackOff", "OOMKilled", "Error"}:
            previous_stdout, _ = _fetch_logs(pod.namespace, pod.name, previous=True)

        combined = "\n".join(part for part in (previous_stdout, stdout) if part)
        if not combined and error:
            snippets.append(
                PodLogSnippet(name=pod.name, namespace=pod.namespace, error=error)
            )
            continue

        snippets.append(
            PodLogSnippet(
                name=pod.name,
                namespace=pod.namespace,
                lines=_relevant_lines(combined),
                error=None if combined else error,
            )
        )

    logger.info("Collected logs for {} failed pods", len(snippets))
    return LogsInvestigation(failed_pod_logs=snippets)
