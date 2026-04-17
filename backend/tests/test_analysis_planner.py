from app.services.analysis_planner import (
    BACKEND_ROUTERS_STITCH_GLOB_DEFAULT,
    FRONTEND_STITCH_GLOB_DEFAULT,
    build_analysis_plan,
)


def test_analysis_planner_enables_stitch_and_schema_paths() -> None:
    plan = build_analysis_plan(
        [
            "frontend/app/dashboard/page.tsx",
            "backend/app/routers/orgs.py",
            "supabase/migrations/20260417000000_gated_analysis.sql",
        ],
        org_settings={"async_checks_enabled": True},
    )

    node_ids = {node["id"] for node in plan["task_graph"]["nodes"]}

    assert FRONTEND_STITCH_GLOB_DEFAULT == "frontend/app/**"
    assert BACKEND_ROUTERS_STITCH_GLOB_DEFAULT == "backend/app/routers/**"
    assert plan["analysis_mode"] == "standard"
    assert "frontend_backend_stitch" in node_ids
    assert "schema_extraction" in node_ids
    assert "route_binding_verifier" in node_ids
    assert plan["reason_json"]["migration_files_changed"] is True
    assert plan["reason_json"]["cpg_wanted"] is True
    assert "cpg_mining" in node_ids


def test_analysis_planner_cpg_always_without_stitch() -> None:
    plan = build_analysis_plan(
        ["backend/app/main.py"],
        org_settings={"cpg_contract_analysis": "always"},
    )
    node_ids = {node["id"] for node in plan["task_graph"]["nodes"]}
    assert "cpg_mining" in node_ids
    assert "frontend_backend_stitch" not in node_ids
    path = next(n for n in plan["task_graph"]["nodes"] if n["id"] == "path_miner")
    assert path["deps"] == ["cpg_mining"]


def test_analysis_planner_respects_global_cpg_bridge_disabled() -> None:
    plan = build_analysis_plan(
        [
            "frontend/app/dashboard/page.tsx",
            "backend/app/routers/orgs.py",
        ],
        org_settings={"cpg_contract_analysis": "always"},
        cpg_bridge_enabled=False,
    )
    node_ids = {node["id"] for node in plan["task_graph"]["nodes"]}
    assert "cpg_mining" not in node_ids
    assert plan["reason_json"]["cpg_contract_analysis"] == "off"


def test_analysis_planner_cpg_off_disables_mining() -> None:
    plan = build_analysis_plan(
        [
            "frontend/app/dashboard/page.tsx",
            "backend/app/routers/orgs.py",
        ],
        org_settings={"cpg_contract_analysis": "off"},
    )
    node_ids = {node["id"] for node in plan["task_graph"]["nodes"]}
    assert "cpg_mining" not in node_ids


def test_analysis_planner_uses_focused_scan_for_small_non_migration_diff() -> None:
    plan = build_analysis_plan(
        ["frontend/app/dashboard/page.tsx", "frontend/app/layout.tsx"],
        org_settings={"focused_contract_scan_max_changed_files": 5},
    )

    assert plan["analysis_mode"] == "focused_contract_scan"
    assert any(
        row["task_id"] == "route_extraction" for row in plan["disabled_subtasks"]
    )
    assert any(row["task_id"] == "cpg_mining" for row in plan["disabled_subtasks"])
