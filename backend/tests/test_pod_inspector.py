from unittest.mock import patch

from app.kubernetes.kubectl_executor import KubectlResult
from app.kubernetes.pod_inspector import inspect_pods


def test_inspect_pods_detects_crashloop():
    mock_json = {
        "items": [
            {
                "metadata": {"name": "payment-service", "namespace": "default"},
                "status": {
                    "phase": "Running",
                    "containerStatuses": [
                        {
                            "name": "payment",
                            "state": {"waiting": {"reason": "CrashLoopBackOff", "message": "back-off 10s restarting"}},
                            "restartCount": 5,
                        }
                    ],
                },
            }
        ]
    }

    with patch("app.kubernetes.pod_inspector.kubectl_executor.get_json", return_value=KubectlResult(success=True, command=[], parsed_json=mock_json)):
        res = inspect_pods()
        assert res.healthy is False
        assert len(res.problematic_pods) == 1
        assert res.problematic_pods[0].name == "payment-service"
        assert res.problematic_pods[0].status == "CrashLoopBackOff"


def test_inspect_pods_detects_image_pull_backoff():
    mock_json = {
        "items": [
            {
                "metadata": {"name": "auth-service", "namespace": "default"},
                "status": {
                    "phase": "Pending",
                    "containerStatuses": [
                        {
                            "name": "auth",
                            "state": {"waiting": {"reason": "ImagePullBackOff", "message": "Failed to pull image"}},
                        }
                    ],
                },
            }
        ]
    }

    with patch("app.kubernetes.pod_inspector.kubectl_executor.get_json", return_value=KubectlResult(success=True, command=[], parsed_json=mock_json)):
        res = inspect_pods()
        assert res.healthy is False
        assert res.problematic_pods[0].status == "ImagePullBackOff"


def test_inspect_pods_detects_oom_killed():
    mock_json = {
        "items": [
            {
                "metadata": {"name": "worker", "namespace": "prod"},
                "status": {
                    "phase": "Running",
                    "containerStatuses": [
                        {
                            "name": "worker-task",
                            "state": {},
                            "lastState": {"terminated": {"reason": "OOMKilled", "exitCode": 137}},
                        }
                    ],
                },
            }
        ]
    }

    with patch("app.kubernetes.pod_inspector.kubectl_executor.get_json", return_value=KubectlResult(success=True, command=[], parsed_json=mock_json)):
        res = inspect_pods()
        assert res.healthy is False
        assert res.problematic_pods[0].status == "OOMKilled"


def test_inspect_pods_detects_start_error():
    mock_json = {
        "items": [
            {
                "metadata": {"name": "nginx-crash", "namespace": "default"},
                "status": {
                    "phase": "Failed",
                    "containerStatuses": [
                        {
                            "name": "nginx",
                            "state": {
                                "terminated": {
                                    "reason": "StartError",
                                    "message": "exec: invalid executable",
                                }
                            },
                        }
                    ],
                },
            }
        ]
    }

    with patch("app.kubernetes.pod_inspector.kubectl_executor.get_json", return_value=KubectlResult(success=True, command=[], parsed_json=mock_json)):
        res = inspect_pods(namespace="default")

    assert res.healthy is False
    assert res.problematic_pods[0].name == "nginx-crash"
    assert res.problematic_pods[0].status == "StartError"


def test_inspect_pods_detects_unschedulable_pending():
    mock_json = {
        "items": [
            {
                "metadata": {"name": "batch-job", "namespace": "default"},
                "status": {
                    "phase": "Pending",
                    "conditions": [
                        {
                            "type": "PodScheduled",
                            "status": "False",
                            "reason": "Unschedulable",
                            "message": "0/1 nodes available: insufficient memory",
                        }
                    ],
                },
            }
        ]
    }

    with patch("app.kubernetes.pod_inspector.kubectl_executor.get_json", return_value=KubectlResult(success=True, command=[], parsed_json=mock_json)):
        res = inspect_pods()
        assert res.healthy is False
        assert res.problematic_pods[0].status == "Pending"
        assert "insufficient memory" in (res.problematic_pods[0].message or "")


def test_inspect_pods_all_healthy():
    mock_json = {
        "items": [
            {
                "metadata": {"name": "healthy-pod", "namespace": "default"},
                "status": {
                    "phase": "Running",
                    "containerStatuses": [{"name": "app", "state": {"running": {}}, "restartCount": 0}],
                },
            }
        ]
    }

    with patch("app.kubernetes.pod_inspector.kubectl_executor.get_json", return_value=KubectlResult(success=True, command=[], parsed_json=mock_json)):
        res = inspect_pods()
        assert res.healthy is True
        assert len(res.problematic_pods) == 0
        assert res.total_pods == 1
