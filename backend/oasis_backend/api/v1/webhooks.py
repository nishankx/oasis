"""
GitHub Webhook receiver: tracks PR merges, closures, and CI status checks.
"""

from __future__ import annotations
import json
from typing import Any, Dict
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from oasis_backend.api.deps import get_pr_service
from oasis_backend.models.pr import WebhookEventResponse
from oasis_backend.services.pr_service import PRService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/github", response_model=WebhookEventResponse)
async def github_webhook_receiver(
    request: Request,
    x_github_event: str = Header(..., description="GitHub event header"),
    x_hub_signature_256: str = Header(None, description="HMAC SHA-256 signature"),
    pr_service: PRService = Depends(get_pr_service),
):
    """
    Receives and processes GitHub webhook events:
    - Verifies HMAC signature with X-Hub-Signature-256
    - pull_request (merged -> awards contribution score; closed -> updates status)
    - check_run / status (updates CI run results)
    """
    body_bytes = await request.body()

    # Signature verification
    if not pr_service.verify_webhook_signature(body_bytes, x_hub_signature_256):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub webhook HMAC signature.",
        )

    try:
        payload: Dict[str, Any] = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed JSON payload.")

    result = await pr_service.handle_github_webhook(x_github_event, payload)

    return WebhookEventResponse(
        handled=result.get("handled", False),
        event_type=x_github_event,
        action=payload.get("action"),
        details=result,
    )
