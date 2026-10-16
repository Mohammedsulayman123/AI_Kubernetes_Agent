"""Safe kubectl command runner using subprocess (no Kubernetes Python SDK)."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.core.config import settings

DEFAULT_TIMEOUT_SECONDS = 30


@dataclass
class KubectlResult:
    success: bool
    command: list[str]
    stdout: str = ""
    stderr: str = ""
    return_code: int | None = None
    error: str | None = None
    parsed_json: Any = field(default=None, repr=False)


class KubectlExecutor:
    def __init__(self, kubectl_bin: str = "kubectl") -> None:
        self.kubectl_bin = kubectl_bin
        self._context: str | None = None  # active kubeconfig context

    def set_context(self, context: str | None) -> None:
        """Override the active kubeconfig context for subsequent calls."""
        self._context = context
        if context:
            logger.info("kubectl context set to: {}", context)

    def _resolve_kubeconfig(self) -> str | None:
        path = settings.kubeconfig_path or os.environ.get("KUBECONFIG")
        if not path or not os.path.exists(path):
            return path

        # When running inside Docker, host-bound clusters like kind/minikube specify
        # https://127.0.0.1:<port> or https://localhost:<port>. Inside the container,
        # 127.0.0.1 points to the container itself. Rewrite to host.docker.internal.
        is_container = os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER") == "1"
        if is_container:
            try:
                import yaml

                with open(path, "r", encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                changed = False
                for item in cfg.get("clusters") or []:
                    cluster = item.get("cluster") or {}
                    server = cluster.get("server", "")
                    if "127.0.0.1:" in server or "localhost:" in server:
                        cluster["server"] = server.replace("127.0.0.1:", "host.docker.internal:").replace(
                            "localhost:", "host.docker.internal:"
                        )
                        cluster["tls-server-name"] = "localhost"
                        changed = True
                if changed:
                    tmp_path = "/tmp/kubeconfig_docker"
                    with open(tmp_path, "w", encoding="utf-8") as f:
                        yaml.dump(cfg, f)
                    return tmp_path
            except Exception as exc:
                logger.warning("Could not rewrite container kubeconfig: {}", exc)

        return path

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        kubeconfig = self._resolve_kubeconfig()
        if kubeconfig:
            env["KUBECONFIG"] = kubeconfig
        return env

    def run(
        self,
        args: list[str],
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        parse_json: bool = False,
        context: str | None = None,
    ) -> KubectlResult:
        # A per-call context avoids mutating shared executor state for one-off actions.
        active_context = context if context is not None else self._context
        context_args = ["--context", active_context] if active_context else []
        command = [self.kubectl_bin, *context_args, *args]
        logger.info("Running kubectl: {}", " ".join(command))

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self._env(),
                check=False,
            )
        except FileNotFoundError:
            error = "kubectl is not installed or not on PATH"
            logger.error(error)
            return KubectlResult(success=False, command=command, error=error)
        except subprocess.TimeoutExpired:
            error = f"kubectl timed out after {timeout}s: {' '.join(command)}"
            logger.error(error)
            return KubectlResult(success=False, command=command, error=error)
        except OSError as exc:
            error = f"failed to start kubectl: {exc}"
            logger.error(error)
            return KubectlResult(success=False, command=command, error=error)

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        success = completed.returncode == 0

        if not success:
            raw_error = stderr.strip() or f"kubectl exited with code {completed.returncode}"
            error = _friendly_error(raw_error)
            logger.warning("kubectl failed: {}", raw_error)
            return KubectlResult(
                success=False,
                command=command,
                stdout=stdout,
                stderr=stderr,
                return_code=completed.returncode,
                error=error,
            )

        result = KubectlResult(
            success=True,
            command=command,
            stdout=stdout,
            stderr=stderr,
            return_code=completed.returncode,
        )

        if parse_json:
            try:
                result.parsed_json = json.loads(stdout) if stdout.strip() else {}
            except json.JSONDecodeError as exc:
                error = f"kubectl returned invalid JSON: {exc}"
                logger.error(error)
                result.success = False
                result.error = error

        return result

    def get_json(
        self,
        resource: str,
        extra_args: list[str] | None = None,
        namespace: str | None = None,
        context: str | None = None,
    ) -> KubectlResult:
        scope = ["-n", namespace] if namespace else ["-A"]
        args = ["get", resource, *scope, "-o", "json", "--request-timeout=20s"]
        if extra_args:
            args.extend(extra_args)
        return self.run(args, parse_json=True, context=context)


def _friendly_error(raw: str) -> str:
    """Convert low-level kubectl errors into beginner-friendly messages."""
    low = raw.lower()
    if "connection refused" in low or "unreachable" in low or "no route to host" in low:
        return (
            "Unable to connect to the Kubernetes cluster.\n\n"
            "Please verify:\n"
            "  • kubeconfig path is correct\n"
            "  • cluster is running and reachable\n"
            "  • kubectl permissions are set"
        )
    if "unauthorized" in low or "forbidden" in low:
        return (
            "Authentication / authorization failed.\n\n"
            "Please check:\n"
            "  • Your credentials are valid\n"
            "  • You have the required RBAC permissions"
        )
    if "no such file" in low or "kubeconfig" in low and "not found" in low:
        return (
            "kubeconfig file not found.\n\n"
            "Make sure kubectl is configured:\n"
            "  kubectl config view"
        )
    if "timeout" in low:
        return (
            "kubectl request timed out.\n\n"
            "The cluster may be under load or unreachable. Try again shortly."
        )
    return raw


kubectl_executor = KubectlExecutor()

