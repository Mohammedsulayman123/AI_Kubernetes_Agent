from __future__ import annotations

from fastapi import APIRouter

from pydantic import BaseModel
from app.models.investigation import InvestigationResponse
from app.services.investigation import investigate_cluster

router = APIRouter(tags=["investigation"])


class InvestigateRequest(BaseModel):
    channel: str = "investigations"
    context: str | None = None  # kubeconfig context name (cluster)
    namespace: str | None = None  # optional namespace scope for targeted diagnosis
    pod_name: str | None = None  # optional pod scope within the namespace


@router.post(
    "/investigate",
    response_model=InvestigationResponse,
    summary="Run Kubernetes investigation + AI diagnosis",
    description=(
        "Collects Kubernetes evidence (pods, logs, events, deployments, networking) "
        "and runs the AI reasoning engine to produce a root cause analysis with "
        "suggested fix and confidence score."
    ),
)
def post_investigate(body: InvestigateRequest | None = None) -> InvestigationResponse:
    channel = body.channel if body and body.channel else "investigations"
    context = body.context if body else None
    namespace = body.namespace if body else None
    pod_name = body.pod_name if body else None
    return investigate_cluster(channel=channel, context=context, namespace=namespace, pod_name=pod_name)

