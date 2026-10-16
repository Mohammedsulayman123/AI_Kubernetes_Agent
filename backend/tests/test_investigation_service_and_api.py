from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.investigation import (
    DeploymentInvestigation,
    EventsInvestigation,
    InvestigationPayload,
    InvestigationResponse,
    LogsInvestigation,
    NetworkInvestigation,
    PodInvestigation,
    ProblematicPod,
)
from app.services.investigation import investigate_cluster

client = TestClient(app)


def test_investigate_cluster_service_flow():
    with (
        patch("app.services.investigation.inspect_pods") as mock_pods,
        patch("app.services.investigation.collect_logs") as mock_logs,
        patch("app.services.investigation.analyze_events") as mock_events,
        patch("app.services.investigation.inspect_deployments") as mock_deploy,
        patch("app.services.investigation.list_pod_snapshots", return_value=([], None)),
        patch("app.services.investigation.inspect_network") as mock_net,
    ):
        mock_pods.return_value = PodInvestigation(
            healthy=False,
            problematic_pods=[ProblematicPod(name="pod-1", namespace="default", status="CrashLoopBackOff")],
            total_pods=1,
        )
        mock_logs.return_value = LogsInvestigation(failed_pod_logs=[])
        mock_events.return_value = EventsInvestigation(healthy=True, findings=[])
        mock_deploy.return_value = DeploymentInvestigation(healthy=True, unhealthy_deployments=[], total_deployments=1)
        mock_net.return_value = NetworkInvestigation(healthy=True, issues=[], total_services=1)

        res = investigate_cluster()

        assert res.status == "success"
        assert res.investigation.pods.healthy is False
        assert len(res.investigation.pods.problematic_pods) == 1
        assert res.investigation.deployments.healthy is True
        assert res.investigation.network.healthy is True


def test_post_investigate_api_endpoint():
    response = client.post("/investigate")
    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert "investigation" in data
    assert "pods" in data["investigation"]
    assert "logs" in data["investigation"]
    assert "events" in data["investigation"]
    assert "deployments" in data["investigation"]
    assert "network" in data["investigation"]
