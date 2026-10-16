from unittest.mock import patch

from app.kubernetes.deployment_inspector import inspect_deployments
from app.kubernetes.kubectl_executor import KubectlResult


def test_inspect_deployments_rollout_failure():
    mock_deployments = {
        "items": [
            {
                "metadata": {"name": "frontend", "namespace": "default"},
                "spec": {"replicas": 3},
                "status": {
                    "availableReplicas": 1,
                    "unavailableReplicas": 2,
                    "updatedReplicas": 3,
                    "conditions": [
                        {
                            "type": "Progressing",
                            "status": "False",
                            "reason": "ProgressDeadlineExceeded",
                            "message": "ReplicaSet timed out",
                        }
                    ],
                },
            }
        ]
    }

    with patch("app.kubernetes.deployment_inspector.kubectl_executor.get_json", return_value=KubectlResult(success=True, command=[], parsed_json=mock_deployments)):
        res = inspect_deployments()
        assert res.healthy is False
        assert len(res.unhealthy_deployments) == 1
        d = res.unhealthy_deployments[0]
        assert d.name == "frontend"
        assert "ProgressDeadlineExceeded" in d.issue
        assert d.desired_replicas == 3
        assert d.available_replicas == 1
        assert d.unavailable_replicas == 2


def test_inspect_deployments_unavailable_replicas():
    mock_deployments = {
        "items": [
            {
                "metadata": {"name": "api", "namespace": "default"},
                "spec": {"replicas": 2},
                "status": {
                    "availableReplicas": 0,
                    "unavailableReplicas": 2,
                    "conditions": [],
                },
            }
        ]
    }

    with patch("app.kubernetes.deployment_inspector.kubectl_executor.get_json", return_value=KubectlResult(success=True, command=[], parsed_json=mock_deployments)):
        res = inspect_deployments()
        assert res.healthy is False
        assert len(res.unhealthy_deployments) == 1
        assert "unavailable replica" in res.unhealthy_deployments[0].issue


def test_inspect_deployments_all_healthy():
    mock_deployments = {
        "items": [
            {
                "metadata": {"name": "api", "namespace": "default"},
                "spec": {"replicas": 2},
                "status": {
                    "availableReplicas": 2,
                    "unavailableReplicas": 0,
                    "updatedReplicas": 2,
                    "conditions": [{"type": "Available", "status": "True"}],
                },
            }
        ]
    }

    with patch("app.kubernetes.deployment_inspector.kubectl_executor.get_json", return_value=KubectlResult(success=True, command=[], parsed_json=mock_deployments)):
        res = inspect_deployments()
        assert res.healthy is True
        assert len(res.unhealthy_deployments) == 0
        assert res.total_deployments == 1
