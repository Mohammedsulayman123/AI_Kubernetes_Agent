from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import httpx
from loguru import logger

from app.core.config import settings


def publish_progress(
    step: str,
    message: str,
    status: str = "done",
    channel: str = "investigations",
    meta: dict[str, Any] | None = None,
) -> None:
    """Emit a realtime progress event to InsForge Socket.IO subscribers via Postgres RPC."""
    if not settings.insforge_base_url or not settings.insforge_anon_key:
        return

    url = f"{settings.insforge_base_url.rstrip('/')}/api/database/rpc/publish_realtime"
    headers = {
        "apikey": settings.insforge_anon_key,
        "Authorization": f"Bearer {settings.insforge_anon_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "channel": channel,
        "event": "progress",
        "payload": {
            "step": step,
            "message": message,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(meta or {}),
        },
    }

    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                logger.warning(
                    "Realtime event publish returned status={}: {}",
                    resp.status_code,
                    resp.text,
                )
    except Exception as exc:
        logger.warning("Failed to publish realtime progress event: {}", exc)
