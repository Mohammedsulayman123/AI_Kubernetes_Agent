"""API routes for injecting and cleaning up Kubernetes test failure scenarios."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from app.services.test_scenarios import apply_scenario, cleanup_scenario, list_scenarios

router = APIRouter(tags=["test-scenarios"])


class ScenarioRequest(BaseModel):
    scenario_id: str
    context: str | None = None


@router.get(
    "/test-scenarios",
    summary="List available failure test scenarios",
)
def get_scenarios():
    return {"scenarios": list_scenarios()}


@router.post(
    "/test-scenarios/apply",
    summary="Apply a test failure scenario to the cluster",
)
def post_apply_scenario(body: ScenarioRequest):
    return apply_scenario(scenario_id=body.scenario_id, context=body.context)


@router.post(
    "/test-scenarios/cleanup",
    summary="Remove resources created by a test scenario",
)
def post_cleanup_scenario(body: ScenarioRequest):
    return cleanup_scenario(scenario_id=body.scenario_id, context=body.context)
