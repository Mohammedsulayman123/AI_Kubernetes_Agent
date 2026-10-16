from unittest.mock import patch

import yaml

from app.kubernetes.kubectl_executor import KubectlResult
from app.services.test_scenarios import SCENARIOS, apply_scenario, cleanup_scenario


def test_crashloopbackoff_manifest_is_valid_yaml():
    documents = list(yaml.safe_load_all(SCENARIOS["crashloopbackoff"]["manifest"]))

    assert documents[0]["kind"] == "Deployment"


def test_apply_scenario_uses_docker_aware_kubectl_executor():
    success = KubectlResult(success=True, command=[], stdout="deployment.apps/crash-test created\n")
    ready = KubectlResult(
        success=True,
        command=[],
        parsed_json={"items": [{"status": {"containerStatuses": [{"state": {"waiting": {"reason": "CrashLoopBackOff"}}}]}}]},
    )

    with patch("app.services.test_scenarios.kubectl_executor.run", side_effect=[success, ready]) as run:
        result = apply_scenario("crashloopbackoff", context="kind-demo")

    assert result["success"] is True
    assert result["output"] == "deployment.apps/crash-test created"
    args = run.call_args_list[0].args[0]
    assert args[:2] == ["apply", "-f"]
    assert run.call_args_list[0].kwargs == {"timeout": 30, "context": "kind-demo"}
    assert result["namespace"] == "agent-test-crashloop"


def test_apply_scenario_returns_executor_error():
    failure = KubectlResult(success=False, command=[], error="Unable to connect to the Kubernetes cluster.")

    with patch("app.services.test_scenarios.kubectl_executor.run", return_value=failure):
        result = apply_scenario("imagepullbackoff")

    assert result == {"success": False, "error": failure.error}


def test_cleanup_scenario_reports_delete_failure():
    failure = KubectlResult(success=False, command=[], error="forbidden")

    with patch("app.services.test_scenarios.kubectl_executor.run", return_value=failure):
        result = cleanup_scenario("crashloopbackoff", context="kind-demo")

    assert result["success"] is False
    assert result["error"] == "forbidden"
