from unittest.mock import patch

from app.kubernetes.kubectl_executor import KubectlResult
from app.kubernetes.network_inspector import inspect_network


def test_inspect_network_missing_selector():
    mock_svc = {
        "items": [
            {
                "metadata": {"name": "orphan-svc", "namespace": "default"},
                "spec": {"type": "ClusterIP", "selector": {}},
            }
        ]
    }
    mock_ep = {"items": []}

    with patch("app.kubernetes.network_inspector.kubectl_executor.get_json") as mock_get:
        mock_get.side_effect = [
            KubectlResult(success=True, command=[], parsed_json=mock_svc),
            KubectlResult(success=True, command=[], parsed_json=mock_ep),
        ]
        res = inspect_network(pod_items=[])
        assert res.healthy is False
        assert any(i.issue == "missing selector" for i in res.issues)


def test_inspect_network_selector_mismatch():
    mock_svc = {
        "items": [
            {
                "metadata": {"name": "web-svc", "namespace": "default"},
                "spec": {"type": "ClusterIP", "selector": {"app": "web"}},
            }
        ]
    }
    mock_ep = {"items": []}
    pod_items = [
        {
            "metadata": {"name": "db-pod", "namespace": "default", "labels": {"app": "db"}},
            "status": {"phase": "Running"},
        }
    ]

    with patch("app.kubernetes.network_inspector.kubectl_executor.get_json") as mock_get:
        mock_get.side_effect = [
            KubectlResult(success=True, command=[], parsed_json=mock_svc),
            KubectlResult(success=True, command=[], parsed_json=mock_ep),
        ]
        res = inspect_network(pod_items=pod_items)
        assert res.healthy is False
        assert any(i.issue == "selector mismatch" for i in res.issues)


def test_inspect_network_missing_endpoints():
    mock_svc = {
        "items": [
            {
                "metadata": {"name": "web-svc", "namespace": "default"},
                "spec": {"type": "ClusterIP", "selector": {"app": "web"}},
            }
        ]
    }
    mock_ep = {
        "items": [
            {
                "metadata": {"name": "web-svc", "namespace": "default"},
                "subsets": [{"addresses": []}],  # 0 ready addresses
            }
        ]
    }
    pod_items = [
        {
            "metadata": {"name": "web-pod-1", "namespace": "default", "labels": {"app": "web"}},
            "status": {"phase": "Running"},
        }
    ]

    with patch("app.kubernetes.network_inspector.kubectl_executor.get_json") as mock_get:
        mock_get.side_effect = [
            KubectlResult(success=True, command=[], parsed_json=mock_svc),
            KubectlResult(success=True, command=[], parsed_json=mock_ep),
        ]
        res = inspect_network(pod_items=pod_items)
        assert res.healthy is False
        assert any(i.issue == "missing endpoints" for i in res.issues)


def test_inspect_network_dns_pod_unhealthy():
    mock_svc = {"items": []}
    mock_ep = {"items": []}
    pod_items = [
        {
            "metadata": {
                "name": "coredns-559f6c778d-8xt48",
                "namespace": "kube-system",
                "labels": {"k8s-app": "kube-dns"},
            },
            "status": {"phase": "CrashLoopBackOff"},
        }
    ]

    with patch("app.kubernetes.network_inspector.kubectl_executor.get_json") as mock_get:
        mock_get.side_effect = [
            KubectlResult(success=True, command=[], parsed_json=mock_svc),
            KubectlResult(success=True, command=[], parsed_json=mock_ep),
        ]
        res = inspect_network(pod_items=pod_items)
        assert res.healthy is False
        assert any("DNS-related pod not Running" in i.issue for i in res.issues)
