import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Request, status
from supabase import create_client

from app.config import settings
from app.worker.tasks import schedule_analysis_job

log = logging.getLogger(__name__)

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


def _sb():
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return None
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


@router.post("/webhook")
async def github_webhook(
    request: Request,
    background: BackgroundTasks,
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    x_github_event: str | None = Header(None, alias="X-GitHub-Event"),
) -> dict[str, Any]:
    body = await request.body()
    if settings.github_webhook_secret and not _verify_github_signature(
        body,
        x_hub_signature_256,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    sb = _sb()
    if sb is None:
        return {"received": True, "queued": False, "reason": "supabase_not_configured"}

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return {"received": True, "queued": False, "reason": "invalid_json"}

    event = x_github_event or ""

    if event == "pull_request":
        action = payload.get("action")
        if action not in ("opened", "synchronize", "reopened", "edited"):
            return {"received": True, "queued": False, "reason": f"action_{action}"}
        pr = payload.get("pull_request") or {}
        repo = payload.get("repository") or {}
        gh_repo_id = repo.get("id")
        if not gh_repo_id:
            return {"received": True, "queued": False, "reason": "no_repository"}
        rres = (
            sb.table("repositories")
            .select("id")
            .eq("github_repo_id", int(gh_repo_id))
            .limit(1)
            .execute()
        )
        if not rres.data:
            return {"received": True, "queued": False, "reason": "repo_not_registered"}
        repo_uuid = rres.data[0]["id"]
        base_sha = (pr.get("base") or {}).get("sha")
        head_sha = (pr.get("head") or {}).get("sha")
        pr_number = pr.get("number")
        if not base_sha or not head_sha:
            return {"received": True, "queued": False, "reason": "missing_shas"}
        row = {
            "repo_id": str(repo_uuid),
            "pr_number": pr_number,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "status": "pending",
            "summary_json": {},
        }
        ins = sb.table("pr_analyses").insert(row).execute()
        if not ins.data:
            return {"received": True, "queued": False, "reason": "insert_failed"}
        analysis_id = ins.data[0]["id"]
        schedule_analysis_job(str(analysis_id), background)
        return {"received": True, "queued": True, "analysis_id": str(analysis_id)}

    if event == "installation":
        inst = payload.get("installation") or {}
        iid = inst.get("id")
        acct = (inst.get("account") or {}).get("login", "")
        action = payload.get("action")
        if action == "created" and iid:
            log.info("GitHub installation %s for %s — link org in app", iid, acct)
        return {"received": True, "queued": False, "event": "installation"}

    return {"received": True, "queued": False, "event": event or "unknown"}
