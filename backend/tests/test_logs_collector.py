from unittest.mock import patch

from app.kubernetes.kubectl_executor import KubectlResult
from app.kubernetes.logs_collector import collect_logs
from app.models.investigation import ProblematicPod


def test_collect_logs_empty_problematic():
    res = collect_logs([])
    assert res.failed_pod_logs == []
    assert res.error is None


def test_collect_logs_relevant_lines_filter():
    pod = ProblematicPod(name="payment-service", namespace="default", status="CrashLoopBackOff")

    fake_logs = (
        "INFO Starting up\n"
        "DEBUG Connecting to database\n"
        "ERROR Failed to connect to postgres: connection refused\n"
        "INFO Retrying in 5 seconds\n"
        "FATAL Fatal panic: unable to load configuration\n"
    )

    with patch("app.kubernetes.logs_collector.kubectl_executor.run") as mock_run:
        mock_run.side_effect = [
            KubectlResult(success=True, command=[], stdout=fake_logs),
            KubectlResult(success=False, command=[], error="previous terminated container not found"),
        ]
        res = collect_logs([pod])
        assert len(res.failed_pod_logs) == 1
        snippet = res.failed_pod_logs[0]
        assert snippet.name == "payment-service"
        assert len(snippet.lines) == 2
        assert any("connection refused" in line for line in snippet.lines)
        assert any("Fatal panic" in line for line in snippet.lines)


def test_collect_logs_unsafe_name_skipped():
    pod = ProblematicPod(name="malicious;rm -rf /", namespace="default", status="CrashLoopBackOff")

    res = collect_logs([pod])
    assert len(res.failed_pod_logs) == 1
    assert "skipped unsafe" in (res.failed_pod_logs[0].error or "")
