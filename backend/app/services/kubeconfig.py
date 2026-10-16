"""Read the local kubeconfig and return a list of available contexts/clusters."""

from __future__ import annotations

import os
from typing import Any

import yaml
from loguru import logger


def _kubeconfig_path() -> str:
    return os.environ.get("KUBECONFIG") or os.path.expanduser("~/.kube/config")


def list_clusters() -> dict[str, Any]:
    """Parse the kubeconfig file and return contexts + current context."""
    path = _kubeconfig_path()

    if not os.path.exists(path):
        logger.warning("kubeconfig not found at {}", path)
        return {
            "current_context": None,
            "clusters": [],
            "error": (
                f"kubeconfig file not found at {path}. "
                "Please ensure kubectl is configured on this machine."
            ),
        }

    try:
        with open(path, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
    except Exception as exc:
        logger.error("Failed to read kubeconfig: {}", exc)
        return {
            "current_context": None,
            "clusters": [],
            "error": f"Failed to read kubeconfig: {exc}",
        }

    raw_contexts = cfg.get("contexts") or []
    raw_clusters = cfg.get("clusters") or []
    current_context = cfg.get("current-context") or ""

    # Build a quick lookup: cluster-name → server URL
    cluster_server: dict[str, str] = {}
    for c in raw_clusters:
        name = c.get("name") or ""
        server = (c.get("cluster") or {}).get("server") or ""
        cluster_server[name] = server

    clusters: list[dict[str, Any]] = []
    for ctx in raw_contexts:
        ctx_name = ctx.get("name") or ""
        ctx_cluster = (ctx.get("context") or {}).get("cluster") or ""
        ctx_namespace = (ctx.get("context") or {}).get("namespace") or "default"
        clusters.append(
            {
                "context": ctx_name,
                "cluster": ctx_cluster,
                "namespace": ctx_namespace,
                "server": cluster_server.get(ctx_cluster, ""),
                "is_current": ctx_name == current_context,
            }
        )

    logger.info(
        "kubeconfig loaded: {} contexts, current={}",
        len(clusters),
        current_context,
    )
    return {
        "current_context": current_context,
        "clusters": clusters,
        "error": None,
    }
