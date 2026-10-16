"""Pydantic models for the AI diagnosis output."""

from pydantic import BaseModel, Field


class Diagnosis(BaseModel):
    """Structured AI reasoning output from the Senior SRE agent."""

    root_cause: str
    """Short, specific root cause statement (1-2 sentences)."""

    explanation: str
    """Deeper explanation correlating pods, logs, events, and deployments."""

    fix: str
    """Actionable fix description in plain language."""

    kubectl_commands: list[str] = Field(default_factory=list)
    """Runnable kubectl commands that apply the fix."""

    prevention: str = ""
    """Recommendation to prevent this class of failure in future."""

    confidence: int = 0
    """Confidence score 0-100 based on evidence quality."""

    confidence_reasoning: str = ""
    """Brief explanation of why the confidence score was assigned."""

    skipped: bool = False
    """True when cluster is healthy and no AI call was needed."""

    error: str | None = None
    """Set when the LLM call failed; investigation evidence is still returned."""
