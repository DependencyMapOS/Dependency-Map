"""GitHub App installation token, tarball download, compare API, CODEOWNERS."""

from __future__ import annotations

import io
import logging
import sys
import tarfile
import time
from pathlib import Path
from typing import Any

import httpx
import jwt

from app.config import settings

log = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
API_ACCEPT = "application/vnd.github+json"
API_VERSION = "2022-11-28"


def _pem() -> str:
    raw = settings.github_app_private_key.strip()
    if not raw:
        return ""
    return raw.replace("\\n", "\n")


def _app_jwt() -> str:
    app_id = settings.github_app_id.strip()
    pem = _pem()
    if not app_id or not pem:
        raise RuntimeError("GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY must be set")
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + 9 * 60,
        "iss": app_id,
    }
    return jwt.encode(payload, pem, algorithm="RS256")


def get_installation_token(installation_id: int) -> str:
    """Exchange GitHub App JWT for an installation access token."""
    gh_jwt = _app_jwt()
    url = f"{GITHUB_API}/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {gh_jwt}",
        "Accept": API_ACCEPT,
        "X-GitHub-Api-Version": API_VERSION,
    }
    with httpx.Client(timeout=60.0) as client:
        r = client.post(url, headers=headers)
        r.raise_for_status()
        data = r.json()
    token = data.get("token")
    if not token:
        raise RuntimeError("GitHub returned no installation token")
    return str(token)


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": API_ACCEPT,
        "X-GitHub-Api-Version": API_VERSION,
    }


def fetch_tarball_to_dir(full_name: str, sha: str, token: str, dest_dir: Path) -> Path:
    """
    Download repo tarball for commit sha and extract into dest_dir.
    Returns the root folder containing extracted files (first member prefix).
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    url = f"{GITHUB_API}/repos/{full_name}/tarball/{sha}"
    with httpx.Client(timeout=120.0, follow_redirects=True) as client:
        r = client.get(url, headers=_auth_headers(token))
        r.raise_for_status()
        data = r.content

    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        if sys.version_info >= (3, 12):
            tf.extractall(dest_dir, filter="data")
        else:
            tf.extractall(dest_dir)

    # GitHub tarball is one top-level dir: {owner}-{repo}-{sha}/
    subdirs = [p for p in dest_dir.iterdir() if p.is_dir()]
    if len(subdirs) != 1:
        log.warning("Expected one root dir in tarball, got %s", subdirs)
        return dest_dir
    return subdirs[0]


def compare_commits(
    full_name: str,
    base_sha: str,
    head_sha: str,
    token: str,
) -> dict[str, Any]:
    """GET /compare/{base}...{head}"""
    url = f"{GITHUB_API}/repos/{full_name}/compare/{base_sha}...{head_sha}"
    with httpx.Client(timeout=60.0) as client:
        r = client.get(url, headers=_auth_headers(token))
        r.raise_for_status()
        return r.json()


def changed_files_from_compare(compare_json: dict[str, Any]) -> list[str]:
    files = compare_json.get("files") or []
    names: list[str] = []
    for f in files:
        if isinstance(f, dict) and f.get("filename"):
            names.append(str(f["filename"]))
    return names


def fetch_codeowners_text(full_name: str, sha: str, token: str) -> str | None:
    """Return CODEOWNERS raw text if present at root or .github/."""
    paths = ["CODEOWNERS", ".github/CODEOWNERS"]
    with httpx.Client(timeout=30.0) as client:
        for p in paths:
            url = f"{GITHUB_API}/repos/{full_name}/contents/{p}"
            r = client.get(
                url,
                headers=_auth_headers(token),
                params={"ref": sha},
            )
            if r.status_code != 200:
                continue
            body = r.json()
            if isinstance(body, dict) and body.get("encoding") == "base64":
                import base64

                raw = base64.b64decode(body.get("content", "")).decode(
                    "utf-8", errors="replace"
                )
                return raw
    return None


def github_configured() -> bool:
    return bool(settings.github_app_id.strip() and settings.github_app_private_key.strip())
