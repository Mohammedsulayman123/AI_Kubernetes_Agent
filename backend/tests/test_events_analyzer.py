from unittest.mock import patch

from app.kubernetes.events_analyzer import analyze_events
from app.kubernetes.kubectl_executor import KubectlResult


def test_analyze_events_watched_reasons():
    mock_events = {
        "items": [
            {
                "reason": "FailedScheduling",
                "metadata": {"namespace": "default"},
                "involvedObject": {"kind": "Pod", "name": "pod-1", "namespace": "default"},
                "count": 5,
                "message": "0/1 nodes available",
            },
            {
                "reason": "SuccessfulCreate",  # should be ignored
                "metadata": {"namespace": "default"},
                "involvedObject": {"kind": "ReplicaSet", "name": "rs-1", "namespace": "default"},
                "count": 1,
                "message": "Created pod",
            },
            {
                "reason": "ErrImagePull",
                "metadata": {"namespace": "prod"},
                "involvedObject": {"kind": "Pod", "name": "pod-2", "namespace": "prod"},
                "count": 10,
                "message": "rpc error: image not found",
            },
        ]
    }

    with patch("app.kubernetes.events_analyzer.kubectl_executor.get_json", return_value=KubectlResult(success=True, command=[], parsed_json=mock_events)):
        res = analyze_events()
        assert res.healthy is False
        assert len(res.findings) == 2
        # Highest count first
        assert res.findings[0].reason == "ErrImagePull"
        assert res.findings[0].count == 10
        assert res.findings[1].reason == "FailedScheduling"
        assert res.findings[1].count == 5


def test_analyze_events_clean():
    mock_events = {"items": [{"reason": "Started"}, {"reason": "Pulled"}]}

    with patch("app.kubernetes.events_analyzer.kubectl_executor.get_json", return_value=KubectlResult(success=True, command=[], parsed_json=mock_events)):
        res = analyze_events()
        assert res.healthy is True
        assert len(res.findings) == 0
