"""Tests for the AI reasoning layer:
- prompt_builder: evidence formatting + healthy-cluster detection
- analyzer: JSON parse / fence strip / confidence clamp / error capture
- agent: healthy fast-path, LLM error capture, end-to-end with mock
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from app.ai.analyzer import healthy_cluster_diagnosis, parse_diagnosis
from app.ai.prompt_builder import (
    SYSTEM_PROMPT,
    build_user_prompt,
    is_cluster_healthy,
)
from app.models.diagnosis import Diagnosis
from app.models.investigation import (
    DeploymentInvestigation,
    EventsInvestigation,
    InvestigationPayload,
    LogsInvestigation,
    NetworkInvestigation,
    PodInvestigation,
    ProblematicPod,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _healthy_payload() -> InvestigationPayload:
    return InvestigationPayload(
        pods=PodInvestigation(healthy=True, total_pods=3),
        logs=LogsInvestigation(),
        events=EventsInvestigation(healthy=True),
        deployments=DeploymentInvestigation(healthy=True, total_deployments=2),
        network=NetworkInvestigation(healthy=True, total_services=4),
    )


def _unhealthy_payload() -> InvestigationPayload:
    return InvestigationPayload(
        pods=PodInvestigation(
            healthy=False,
            total_pods=5,
            problematic_pods=[
                ProblematicPod(
                    name="api-7d6f9-abc",
                    namespace="default",
                    status="CrashLoopBackOff",
                    message="Back-off restarting failed container",
                    age_seconds=300,
                )
            ],
        ),
        logs=LogsInvestigation(),
        events=EventsInvestigation(healthy=True),
        deployments=DeploymentInvestigation(healthy=True, total_deployments=2),
        network=NetworkInvestigation(healthy=True, total_services=4),
    )


# ─── prompt_builder ───────────────────────────────────────────────────────────


def test_is_cluster_healthy_true_for_all_green():
    assert is_cluster_healthy(_healthy_payload()) is True


def test_is_cluster_healthy_false_when_pods_unhealthy():
    payload = _unhealthy_payload()
    assert is_cluster_healthy(payload) is False


def test_build_user_prompt_contains_pod_info():
    payload = _unhealthy_payload()
    prompt = build_user_prompt(payload)
    assert "CrashLoopBackOff" in prompt
    assert "api-7d6f9-abc" in prompt


def test_build_user_prompt_contains_all_sections():
    payload = _healthy_payload()
    prompt = build_user_prompt(payload)
    for heading in [
        "Pod Status",
        "Application Logs",
        "Warning Events",
        "Deployment Health",
        "Networking",
    ]:
        assert heading in prompt, f"Missing section: {heading}"


def test_system_prompt_mentions_sre():
    assert "SRE" in SYSTEM_PROMPT or "Site Reliability" in SYSTEM_PROMPT


# ─── analyzer: parse_diagnosis ────────────────────────────────────────────────


_VALID_LLM_RESPONSE = json.dumps(
    {
        "root_cause": "OOM killer terminated the application container.",
        "explanation": "The pod api-7d6f9-abc was killed by the OOM killer repeatedly due to exceeding its memory limit.",
        "fix": "Increase the memory limit for the api Deployment.",
        "kubectl_commands": [
            "kubectl set resources deployment/api --limits=memory=512Mi -n default"
        ],
        "prevention": "Set proper memory requests and limits. Enable VPA.",
        "confidence": 85,
        "confidence_reasoning": "Clear OOM evidence from events and logs.",
    }
)


def test_parse_diagnosis_clean_json():
    diag = parse_diagnosis(_VALID_LLM_RESPONSE)
    assert diag.confidence == 85
    assert "OOM" in diag.root_cause
    assert len(diag.kubectl_commands) == 1
    assert diag.error is None
    assert diag.skipped is False


def test_parse_diagnosis_strips_markdown_fences():
    fenced = f"```json\n{_VALID_LLM_RESPONSE}\n```"
    diag = parse_diagnosis(fenced)
    assert diag.confidence == 85
    assert diag.error is None


def test_parse_diagnosis_strips_plain_fences():
    fenced = f"```\n{_VALID_LLM_RESPONSE}\n```"
    diag = parse_diagnosis(fenced)
    assert diag.confidence == 85


def test_parse_diagnosis_clamps_confidence_above_100():
    data = json.loads(_VALID_LLM_RESPONSE)
    data["confidence"] = 150
    diag = parse_diagnosis(json.dumps(data))
    assert diag.confidence == 100


def test_parse_diagnosis_clamps_confidence_below_0():
    data = json.loads(_VALID_LLM_RESPONSE)
    data["confidence"] = -10
    diag = parse_diagnosis(json.dumps(data))
    assert diag.confidence == 0


def test_parse_diagnosis_handles_invalid_json():
    diag = parse_diagnosis("not json at all {{{")
    assert diag.error is not None
    assert diag.confidence == 0


def test_parse_diagnosis_handles_empty_string():
    diag = parse_diagnosis("")
    assert diag.error is not None


def test_healthy_cluster_diagnosis_skipped_flag():
    diag = healthy_cluster_diagnosis()
    assert diag.skipped is True
    assert diag.confidence >= 90


# ─── agent.run_agent ──────────────────────────────────────────────────────────


def test_run_agent_skips_llm_for_healthy_cluster():
    from app.ai.agent import run_agent

    with patch("app.ai.agent.llm_client") as mock_llm:
        diag = run_agent(_healthy_payload())

    mock_llm.complete.assert_not_called()
    assert diag.skipped is True


def test_run_agent_calls_llm_for_unhealthy_cluster():
    from app.ai.agent import run_agent

    with patch("app.ai.agent.llm_client") as mock_llm:
        mock_llm.complete.return_value = _VALID_LLM_RESPONSE
        diag = run_agent(_unhealthy_payload())

    mock_llm.complete.assert_called_once()
    assert diag.confidence == 85
    assert diag.error is None


def test_run_agent_captures_llm_error():
    from app.ai.agent import run_agent

    with patch("app.ai.agent.llm_client") as mock_llm:
        mock_llm.complete.side_effect = RuntimeError("OPENROUTER_API_KEY is not set")
        diag = run_agent(_unhealthy_payload())

    assert diag.error is not None
    assert "OPENROUTER_API_KEY" in diag.error
    assert diag.confidence == 0
