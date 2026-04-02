"""Parse GitHub CODEOWNERS and map paths to owners."""

from __future__ import annotations

import fnmatch
import re
from pathlib import PurePosixPath


def parse_codeowners(content: str) -> list[tuple[str, list[str]]]:
    """
    Return ordered list of (pattern, owners) from CODEOWNERS text.
    Patterns are normalized with forward slashes.
    """
    rules: list[tuple[str, list[str]]] = []
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        pattern = parts[0]
        owners = parts[1:]
        rules.append((pattern, owners))
    return rules


def _match_pattern(pattern: str, path: str) -> bool:
    """Glob-style match similar to GitHub CODEOWNERS."""
    p = pattern.strip()
    if p.startswith("/"):
        p = p[1:]
        full = path
    else:
        full = path
    if "**" in p or "*" in p or "?" in p:
        if fnmatch.fnmatch(full, p):
            return True
        if fnmatch.fnmatch(full, f"**/{p}"):
            return True
        return False
    return full == p or full.startswith(f"{p}/")


def owners_for_paths(
    codeowners_text: str | None,
    paths: list[str],
) -> dict[str, list[str]]:
    """Map each path to matching owners (last rule wins per GitHub semantics)."""
    if not codeowners_text:
        return {}
    rules = parse_codeowners(codeowners_text)
    result: dict[str, list[str]] = {}
    norm_paths = [PurePosixPath(p).as_posix() for p in paths]
    owners_by_path: dict[str, list[str]] = {p: [] for p in norm_paths}
    for pattern, owners in rules:
        for p in norm_paths:
            if _match_pattern(pattern, p):
                owners_by_path[p] = list(owners)
    for p, ow in owners_by_path.items():
        if ow:
            result[p] = ow
    return result


def suggested_reviewers_from_codeowners(
    codeowners_text: str | None,
    impacted_paths: list[str],
    max_people: int = 12,
) -> list[str]:
    if not codeowners_text:
        return []
    mapping = owners_for_paths(codeowners_text, impacted_paths)
    seen: set[str] = set()
    out: list[str] = []
    for p in impacted_paths:
        for h in mapping.get(PurePosixPath(p).as_posix(), []):
            handle = re.sub(r"^@", "", h)
            if handle not in seen:
                seen.add(handle)
                out.append(handle)
            if len(out) >= max_people:
                return out
    # also iterate any mapped values
    for handles in mapping.values():
        for h in handles:
            handle = re.sub(r"^@", "", h)
            if handle not in seen:
                seen.add(handle)
                out.append(handle)
            if len(out) >= max_people:
                return out
    return out
