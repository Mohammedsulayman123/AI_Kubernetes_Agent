import subprocess
from unittest.mock import MagicMock, patch

from app.kubernetes.kubectl_executor import KubectlExecutor, KubectlResult


def test_kubectl_executor_success():
    executor = KubectlExecutor(kubectl_bin="kubectl")
    mock_proc = MagicMock(returncode=0, stdout='{"items": []}', stderr="")

    with patch("subprocess.run", return_value=mock_proc) as mock_run:
        result = executor.run(["get", "pods"], parse_json=True)

        assert result.success is True
        assert result.return_code == 0
        assert result.parsed_json == {"items": []}
        mock_run.assert_called_once()


def test_kubectl_executor_failure_exit_code():
    executor = KubectlExecutor(kubectl_bin="kubectl")
    mock_proc = MagicMock(returncode=1, stdout="", stderr="Error from server: NotFound")

    with patch("subprocess.run", return_value=mock_proc):
        result = executor.run(["get", "pod", "missing"])

        assert result.success is False
        assert result.return_code == 1
        assert "NotFound" in (result.error or "")


def test_kubectl_executor_file_not_found():
    executor = KubectlExecutor(kubectl_bin="nonexistent-kubectl")

    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = executor.run(["version"])

        assert result.success is False
        assert "not installed" in (result.error or "")


def test_kubectl_executor_timeout():
    executor = KubectlExecutor(kubectl_bin="kubectl")

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="kubectl", timeout=5)):
        result = executor.run(["get", "pods"], timeout=5)

        assert result.success is False
        assert "timed out after 5s" in (result.error or "")


def test_kubectl_executor_invalid_json():
    executor = KubectlExecutor(kubectl_bin="kubectl")
    mock_proc = MagicMock(returncode=0, stdout="not-json", stderr="")

    with patch("subprocess.run", return_value=mock_proc):
        result = executor.run(["get", "pods"], parse_json=True)

        assert result.success is False
        assert "invalid JSON" in (result.error or "")
