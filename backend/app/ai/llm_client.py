"""HTTPX-based OpenRouter LLM client.

Uses the OpenAI-compatible API at https://openrouter.ai/api/v1.
Authentication is via the OPENROUTER_API_KEY environment variable
provisioned by InsForge.
"""

from __future__ import annotations

import json

import httpx
from loguru import logger

from app.core.config import settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "anthropic/claude-3.5-haiku"
DEFAULT_TIMEOUT_SECONDS = 60
MAX_RETRIES = 2


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------


class LLMClient:
    """Minimal OpenRouter chat-completion client built on HTTPX.

    Sends a list of messages to the completions endpoint and returns
    the raw text of the first choice.
    """

    def __init__(self) -> None:
        self.api_key = settings.openrouter_api_key
        self.model = settings.openrouter_model or DEFAULT_MODEL

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ai-kubernetes-agent",
            "X-Title": "AI Kubernetes Agent",
        }

    def _is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> str:
        """Send a chat completion request and return the response text.

        Args:
            system_prompt: Persona and output instructions.
            user_prompt: Evidence and question.
            temperature: Lower = more deterministic. 0.2 works well for SRE tasks.

        Returns:
            Raw text from the LLM's first choice.

        Raises:
            RuntimeError: When the API key is missing or all retries fail.
        """
        if not self._is_configured():
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. "
                "Add it to backend/.env to enable AI reasoning."
            )

        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 2):  # 3 total attempts
            try:
                logger.info(
                    "Calling OpenRouter model={} (attempt {}/{})",
                    self.model,
                    attempt,
                    MAX_RETRIES + 1,
                )
                with httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS) as client:
                    response = client.post(
                        f"{OPENROUTER_BASE_URL}/chat/completions",
                        headers=self._headers(),
                        json=payload,
                    )

                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    logger.info("OpenRouter response received ({} chars)", len(content))
                    return content

                # Non-200 — may be retryable (5xx) or not (4xx)
                error_body = response.text[:400]
                logger.warning(
                    "OpenRouter HTTP {} on attempt {}: {}",
                    response.status_code,
                    attempt,
                    error_body,
                )
                last_error = RuntimeError(
                    f"OpenRouter returned HTTP {response.status_code}: {error_body}"
                )
                # Don't retry client errors (4xx)
                if response.status_code < 500:
                    break

            except httpx.TimeoutException as exc:
                logger.warning("OpenRouter request timed out on attempt {}: {}", attempt, exc)
                last_error = RuntimeError(f"OpenRouter request timed out after {DEFAULT_TIMEOUT_SECONDS}s")

            except httpx.RequestError as exc:
                logger.warning("OpenRouter network error on attempt {}: {}", attempt, exc)
                last_error = RuntimeError(f"Network error calling OpenRouter: {exc}")

        raise last_error or RuntimeError("OpenRouter request failed after all retries")


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

llm_client = LLMClient()
