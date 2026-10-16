"""AI Kubernetes Agent — top-level orchestrator.

Flow:
  1. Check if the cluster is healthy → skip LLM if so.
  2. Build a structured prompt from investigation evidence.
  3. Call OpenRouter via the LLM client.
  4. Parse and return a Diagnosis.
"""

from __future__ import annotations

from loguru import logger

from app.ai.analyzer import healthy_cluster_diagnosis, parse_diagnosis
from app.ai.llm_client import llm_client
from app.ai.prompt_builder import SYSTEM_PROMPT, build_user_prompt, is_cluster_healthy
from app.models.diagnosis import Diagnosis
from app.models.investigation import InvestigationPayload


def run_agent(payload: InvestigationPayload) -> Diagnosis:
    """Run the AI Kubernetes agent on a completed investigation payload.

    Args:
        payload: Evidence collected by the Kubernetes Investigation Layer.

    Returns:
        A Diagnosis containing root cause, fix, and confidence score.
    """
    # Fast path — no LLM call needed for healthy clusters
    if is_cluster_healthy(payload):
        logger.info("Cluster is healthy — skipping AI reasoning")
        return healthy_cluster_diagnosis()

    logger.info("Cluster has issues — starting AI reasoning")

    user_prompt = build_user_prompt(payload)

    try:
        raw_response = llm_client.complete(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
    except RuntimeError as exc:
        logger.error("LLM call failed: {}", exc)
        return Diagnosis(
            root_cause="AI reasoning unavailable.",
            explanation=(
                "The LLM call failed. Review the investigation evidence manually. "
                f"Error: {exc}"
            ),
            fix="Check OPENROUTER_API_KEY in backend/.env and retry.",
            kubectl_commands=[],
            confidence=0,
            confidence_reasoning="LLM unavailable — confidence cannot be determined.",
            error=str(exc),
        )

    return parse_diagnosis(raw_response)
