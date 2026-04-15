"""Shared tree-sitter Parser factory for TS/JS/TSX/JSX (no graph_builder import)."""

from __future__ import annotations


def parser_for_suffix(suffix: str):
    try:
        import tree_sitter_javascript as tsjs  # type: ignore
        import tree_sitter_typescript as tsts  # type: ignore
        from tree_sitter import Language, Parser
    except ImportError:
        return None
    try:
        if suffix == ".tsx":
            return Parser(Language(tsts.language_tsx()))
        if suffix == ".ts":
            return Parser(Language(tsts.language_typescript()))
        if suffix in (".js", ".jsx"):
            return Parser(Language(tsjs.language()))
    except Exception:
        return None
    return None
