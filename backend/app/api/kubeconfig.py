"""API routes for kubeconfig cluster listing."""

from __future__ import annotations

from fastapi import APIRouter
from app.services.kubeconfig import list_clusters

router = APIRouter(tags=["kubeconfig"])


@router.get(
    "/clusters",
    summary="List all Kubernetes contexts from the local kubeconfig",
    description="Reads ~/.kube/config (or $KUBECONFIG) and returns all available contexts.",
)
def get_clusters():
    return list_clusters()
