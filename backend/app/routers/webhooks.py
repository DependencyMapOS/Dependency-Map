import hashlib
import hmac

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.config import settings

router = APIRouter(prefix="/internal/github", tags=["github"])


def _verify_github_signature(body: bytes, signature: str | None) -> bool:
    if not settings.github_webhook_secret or not signature:
        return False
    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhook")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
) -> dict:
    body = await request.body()
    if settings.github_webhook_secret and not _verify_github_signature(
        body,
        x_hub_signature_256,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )
    # Enqueue sync / analyze jobs (worker) — stub
    return {"received": True, "queued": False}
