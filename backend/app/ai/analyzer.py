"""Parse raw LLM text into a structured Diagnosis.

Handles:
- Clean JSON responses
- JSON embedded in markdown code fences
- Partial / malformed JSON (best-effort)
- Healthy-cluster fast-path (no LLM call)
- LLM error capture without dropping investigation evidence
"""

from __future__ import annotations

import json
import re

from loguru import logger

from app.models.diagnosis import Diagnosis

# ---------------------------------------------------------------------------
# JSON extraction helpers
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]+?)```", re.IGNORECASE)


def _extract_json_block(text: str) -> str:
    """Return the first JSON block from text, stripping markdown fences if present."""
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    # Try to find bare JSON object
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text.strip()


# ---------------------------------------------------------------------------
# Confidence engine
# ---------------------------------------------------------------------------


def _clamp_confidence(value: int | float | None) -> int:
    """Clamp a confidence value to [0, 100]."""
    if value is None:
        return 0
    return max(0, min(100, int(value)))


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------


def parse_diagnosis(raw_text: str) -> Diagnosis:
    """Parse an LLM response into a Diagnosis model.

    If parsing fails, returns a Diagnosis with the error field set
    and best-effort partial data where possible.
    """
    extracted = _extract_json_block(raw_text)

    try:
        data = json.loads(extracted)
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse LLM response as JSON: {}\nRaw: {!r}", exc, raw_text[:400])
        return Diagnosis(
            root_cause="Unable to parse LLM response.",
            explanation=raw_text[:1000] if raw_text else "No response received.",
            fix="Manually review the cluster state.",
            confidence=0,
            confidence_reasoning="JSON parse failure — confidence cannot be determined.",
            error=f"JSON decode error: {exc}",
        )

    try:
        confidence_raw = data.get("confidence", 0)
        diagnosis = Diagnosis(
            root_cause=str(data.get("root_cause", "Unknown root cause")),
            explanation=str(data.get("explanation", "")),
            fix=str(data.get("fix", "")),
            kubectl_commands=[str(c) for c in data.get("kubectl_commands", [])],
            prevention=str(data.get("prevention", "")),
            confidence=_clamp_confidence(confidence_raw),
            confidence_reasoning=str(data.get("confidence_reasoning", "")),
        )
        logger.info("Diagnosis parsed: root_cause={!r}  confidence={}", diagnosis.root_cause[:80], diagnosis.confidence)
        return diagnosis

    except Exception as exc:  # noqa: BLE001
        logger.warning("Unexpected error building Diagnosis model: {}", exc)
        return Diagnosis(
            root_cause="Internal error building Diagnosis.",
            explanation=str(data)[:1000],
            fix="Review raw LLM output above.",
            confidence=0,
            confidence_reasoning="Model construction failed.",
            error=str(exc),
        )


def healthy_cluster_diagnosis() -> Diagnosis:
    """Return a pre-built Diagnosis for a fully healthy cluster (skip LLM)."""
    return Diagnosis(
        root_cause="Cluster appears healthy — no anomalies detected.",
        explanation=(
            "All pods, deployments, services, and events passed the automated health checks. "
            "No failing pods, warning events, or networking issues were found."
        ),
        fix="No action required.",
        kubectl_commands=[],
        prevention="Continue monitoring with Prometheus/Grafana and set up alerting for future incidents.",
        confidence=95,
        confidence_reasoning=(
            "All evidence sources reported healthy. Confidence is 95 (not 100) because "
            "some issues — such as slow memory leaks or flapping services — can evade static inspection."
        ),
        skipped=True,
    )
