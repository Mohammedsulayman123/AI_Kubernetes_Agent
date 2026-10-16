"""Inject intentional Kubernetes failure scenarios for testing the AI agent."""

from __future__ import annotations

import tempfile
import time
from typing import Any
from loguru import logger

import yaml

from app.kubernetes.kubectl_executor import kubectl_executor

# ── Scenario YAML definitions ────────────────────────────────────────────────

SCENARIOS: dict[str, dict[str, Any]] = {
    "crashloopbackoff": {
        "namespace": "agent-test-crashloop",
        "expected_states": {"CrashLoopBackOff", "Error"},
        "title": "CrashLoopBackOff — Missing Environment Variable",
        "description": "Deploys a pod that requires a missing env var, causing it to crash immediately.",
        "manifest": """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crash-test
  namespace: default
  labels:
    scenario: crashloopbackoff
spec:
  replicas: 1
  selector:
    matchLabels:
      app: crash-test
  template:
    metadata:
      labels:
        app: crash-test
        scenario: crashloopbackoff
    spec:
      containers:
      - name: crash-test
        image: busybox:1.36
        command: ["sh", "-c", 'echo REQUIRED_VAR=$REQUIRED_VAR; [ -z "$REQUIRED_VAR" ] && exit 1']
        env: []
""",
    },
    "imagepullbackoff": {
        "namespace": "agent-test-imagepull",
        "expected_states": {"ImagePullBackOff", "ErrImagePull"},
        "title": "ImagePullBackOff — Wrong Image Tag",
        "description": "Deploys a pod with a non-existent image tag so Kubernetes cannot pull it.",
        "manifest": """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: imgpull-test
  namespace: default
  labels:
    scenario: imagepullbackoff
spec:
  replicas: 1
  selector:
    matchLabels:
      app: imgpull-test
  template:
    metadata:
      labels:
        app: imgpull-test
        scenario: imagepullbackoff
    spec:
      containers:
      - name: imgpull-test
        image: nginx:this-tag-does-not-exist-9999
""",
    },
    "oomkilled": {
        "namespace": "agent-test-oom",
        "expected_states": {"OOMKilled"},
        "title": "OOMKilled — Low Memory Limit",
        "description": "Deploys a container that intentionally allocates more memory than its limit.",
        "manifest": """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oom-test
  namespace: default
  labels:
    scenario: oomkilled
spec:
  replicas: 1
  selector:
    matchLabels:
      app: oom-test
  template:
    metadata:
      labels:
        app: oom-test
        scenario: oomkilled
    spec:
      containers:
      - name: oom-test
        image: polinux/stress:latest
        command: ["stress"]
        args: ["--vm", "1", "--vm-bytes", "150M", "--vm-hang", "1"]
        resources:
          limits:
            memory: "50Mi"
          requests:
            memory: "10Mi"
""",
    },
    "selector-mismatch": {
        "namespace": "agent-test-selector",
        "expected_states": {"Running"},
        "title": "Service Selector Mismatch — Wrong Labels",
        "description": "Creates a Service whose selector does not match any pod labels.",
        "manifest": """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: selector-test
  namespace: default
  labels:
    scenario: selector-mismatch
spec:
  replicas: 1
  selector:
    matchLabels:
      app: selector-test
  template:
    metadata:
      labels:
        app: selector-test
        scenario: selector-mismatch
    spec:
      containers:
      - name: selector-test
        image: nginx:1.25
---
apiVersion: v1
kind: Service
metadata:
  name: selector-test-svc
  namespace: default
spec:
  selector:
    app: WRONG-LABEL-THAT-MATCHES-NOTHING
  ports:
  - port: 80
    targetPort: 80
""",
    },
}

SCENARIO_READY_TIMEOUT_SECONDS = 90
SCENARIO_POLL_SECONDS = 3


def _scenario_manifest(scenario: dict[str, Any]) -> str:
    """Place every scenario in its own namespace without duplicating manifests."""
    namespace = scenario["namespace"]
    documents = list(yaml.safe_load_all(scenario["manifest"]))
    for document in documents:
        if document and document.get("kind") != "Namespace":
            document.setdefault("metadata", {})["namespace"] = namespace
    documents.insert(
        0,
        {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": namespace}},
    )
    return yaml.safe_dump_all(documents, sort_keys=False)


def _pod_states(items: list[dict[str, Any]]) -> set[str]:
    states: set[str] = set()
    for pod in items:
        for container in (pod.get("status") or {}).get("containerStatuses") or []:
            state = container.get("state") or {}
            last_state = container.get("lastState") or {}
            for phase in (state.get("waiting"), state.get("terminated"), last_state.get("terminated")):
                if phase and phase.get("reason"):
                    states.add(phase["reason"])
            if (pod.get("status") or {}).get("phase") == "Running":
                states.add("Running")
    return states


def _wait_for_expected_state(scenario_id: str, scenario: dict[str, Any], context: str | None) -> str | None:
    deadline = time.monotonic() + SCENARIO_READY_TIMEOUT_SECONDS
    expected = scenario["expected_states"]
    while time.monotonic() < deadline:
        result = kubectl_executor.run(
            ["get", "pods", "-n", scenario["namespace"], "-l", f"scenario={scenario_id}", "-o", "json"],
            timeout=20,
            parse_json=True,
            context=context,
        )
        if not result.success:
            return result.error
        states = _pod_states((result.parsed_json or {}).get("items") or [])
        if states.intersection(expected):
            return None
        time.sleep(SCENARIO_POLL_SECONDS)
    return f"Timed out waiting for expected scenario state: {', '.join(sorted(expected))}."


def apply_scenario(scenario_id: str, context: str | None = None) -> dict[str, Any]:
    """Apply a failure scenario manifest to the cluster."""
    scenario = SCENARIOS.get(scenario_id)
    if not scenario:
        return {"success": False, "error": f"Unknown scenario: {scenario_id}"}

    manifest_yaml = _scenario_manifest(scenario)

    # Write to a temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as f:
        f.write(manifest_yaml)
        tmp_path = f.name

    try:
        result = kubectl_executor.run(
            ["apply", "-f", tmp_path],
            timeout=30,
            context=context,
        )
        if not result.success:
            logger.error("Scenario apply failed: {}", result.error)
            return {"success": False, "error": result.error}

        readiness_error = _wait_for_expected_state(scenario_id, scenario, context)
        if readiness_error:
            return {"success": False, "error": readiness_error}

        logger.info("Scenario '{}' applied successfully", scenario_id)
        return {
            "success": True,
            "scenario": scenario_id,
            "title": scenario["title"],
            "description": scenario["description"],
            "namespace": scenario["namespace"],
            "output": result.stdout.strip(),
        }
    except Exception as exc:
        logger.error("Unexpected error applying scenario: {}", exc)
        return {"success": False, "error": str(exc)}
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def cleanup_scenario(scenario_id: str, context: str | None = None) -> dict[str, Any]:
    """Delete resources created by a test scenario."""
    scenario = SCENARIOS.get(scenario_id)
    if not scenario:
        return {"success": False, "error": f"Unknown scenario: {scenario_id}"}

    result = kubectl_executor.run(
        ["delete", "namespace", scenario["namespace"], "--ignore-not-found=true"],
        timeout=30,
        context=context,
    )
    if not result.success:
        return {"success": False, "error": result.error}
    return {"success": True, "scenario": scenario_id, "output": result.stdout.strip()}


def list_scenarios() -> list[dict[str, Any]]:
    return [
        {
            "id": sid,
            "title": s["title"],
            "description": s["description"],
            "namespace": s["namespace"],
        }
        for sid, s in SCENARIOS.items()
    ]

