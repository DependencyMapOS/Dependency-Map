from app.worker.tasks import _build_cpg_status_summary


def test_cpg_status_skipped_when_bridge_disabled() -> None:
    task_graph = {"nodes": [{"id": "cpg_mining", "status": "pending", "optional": True}]}
    plan = {"reason_json": {}, "disabled_subtasks": []}
    state: dict = {"summary": {}, "partial_outputs": []}
    out = _build_cpg_status_summary(task_graph, plan, state, bridge_enabled=False)
    assert out["mode"] == "skipped_disabled"


def test_cpg_status_ran_when_artifacts_present() -> None:
    task_graph = {
        "nodes": [
            {"id": "cpg_mining", "status": "completed", "optional": True},
            {"id": "path_miner", "status": "completed", "optional": True},
            {"id": "ranker", "status": "completed", "optional": True},
        ]
    }
    plan = {"reason_json": {"cpg_contract_analysis": "always"}, "disabled_subtasks": []}
    state = {
        "summary": {"cpg_candidate_count": 3, "cpg_surfaced_count": 1},
        "cpg_artifacts": object(),
        "partial_outputs": [],
    }
    out = _build_cpg_status_summary(task_graph, plan, state, bridge_enabled=True)
    assert out["mode"] == "ran"
    assert out["cpg_candidate_count"] == 3
