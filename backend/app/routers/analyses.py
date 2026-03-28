from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from app.deps import get_supabase_admin, parse_uuid, verify_supabase_jwt
from app.worker import tasks

router = APIRouter(prefix="/v1/repos", tags=["analyses"])


class AnalyzeBody(BaseModel):
    pr_number: int | None = None
    base_sha: str | None = None
    head_sha: str | None = None


@router.post("/{repo_id}/analyze", status_code=status.HTTP_202_ACCEPTED)
def trigger_analyze(
    repo_id: str,
    body: AnalyzeBody,
    background: BackgroundTasks,
    _user: dict = Depends(verify_supabase_jwt),
    supabase=Depends(get_supabase_admin),
) -> dict[str, Any]:
    rid = parse_uuid(repo_id)
    if body.pr_number is None and (not body.base_sha or not body.head_sha):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide pr_number or both base_sha and head_sha",
        )
    row = {
        "repo_id": str(rid),
        "pr_number": body.pr_number,
        "base_sha": body.base_sha,
        "head_sha": body.head_sha,
        "status": "pending",
        "summary_json": {},
    }
    res = supabase.table("pr_analyses").insert(row).execute()
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create analysis",
        )
    analysis_id = res.data[0]["id"]
    background.add_task(tasks.run_analysis_job, str(analysis_id))
    return {"analysis_id": analysis_id, "status": "pending"}


@router.get("/{repo_id}/analyses/{analysis_id}")
def get_analysis(
    repo_id: str,
    analysis_id: str,
    _user: dict = Depends(verify_supabase_jwt),
    supabase=Depends(get_supabase_admin),
) -> dict[str, Any]:
    rid = parse_uuid(repo_id)
    aid = parse_uuid(analysis_id)
    res = (
        supabase.table("pr_analyses")
        .select("*")
        .eq("id", str(aid))
        .eq("repo_id", str(rid))
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return res.data[0]


@router.get("/{repo_id}/analyses/latest")
def get_latest_analysis(
    repo_id: str,
    _user: dict = Depends(verify_supabase_jwt),
    supabase=Depends(get_supabase_admin),
) -> dict[str, Any]:
    rid = parse_uuid(repo_id)
    res = (
        supabase.table("pr_analyses")
        .select("*")
        .eq("repo_id", str(rid))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No analyses")
    return res.data[0]
