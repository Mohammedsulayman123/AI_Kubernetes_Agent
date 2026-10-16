from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.models.diagnosis import Diagnosis


class ProblematicPod(BaseModel):
    name: str
    namespace: str
    status: str
    message: str | None = None
    age_seconds: int | None = None


class PodInvestigation(BaseModel):
    healthy: bool = True
    problematic_pods: list[ProblematicPod] = Field(default_factory=list)
    total_pods: int = 0
    error: str | None = None


class PodLogSnippet(BaseModel):
    name: str
    namespace: str
    lines: list[str] = Field(default_factory=list)
    error: str | None = None


class LogsInvestigation(BaseModel):
    failed_pod_logs: list[PodLogSnippet] = Field(default_factory=list)
    error: str | None = None


class EventFinding(BaseModel):
    reason: str
    namespace: str
    object_kind: str
    object_name: str
    count: int = 1
    message: str


class EventsInvestigation(BaseModel):
    healthy: bool = True
    findings: list[EventFinding] = Field(default_factory=list)
    error: str | None = None


class UnhealthyDeployment(BaseModel):
    name: str
    namespace: str
    desired_replicas: int = 0
    available_replicas: int = 0
    unavailable_replicas: int = 0
    conditions: list[str] = Field(default_factory=list)
    issue: str


class DeploymentInvestigation(BaseModel):
    healthy: bool = True
    unhealthy_deployments: list[UnhealthyDeployment] = Field(default_factory=list)
    total_deployments: int = 0
    error: str | None = None


class NetworkIssue(BaseModel):
    service: str
    namespace: str
    issue: str
    details: str


class NetworkInvestigation(BaseModel):
    healthy: bool = True
    issues: list[NetworkIssue] = Field(default_factory=list)
    total_services: int = 0
    error: str | None = None


class InvestigationPayload(BaseModel):
    pods: PodInvestigation
    logs: LogsInvestigation
    events: EventsInvestigation
    deployments: DeploymentInvestigation
    network: NetworkInvestigation


class InvestigationResponse(BaseModel):
    status: str
    investigation: InvestigationPayload
    diagnosis: Diagnosis | None = None
    message: str | None = None


# Used internally when passing pod list between inspectors
class PodSnapshot(BaseModel):
    name: str
    namespace: str
    labels: dict[str, str] = Field(default_factory=dict)
    status: str
    raw: dict[str, Any] = Field(default_factory=dict)
