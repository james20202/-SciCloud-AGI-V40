import pytest

from core.execution_engine import ExecutionEngine


def test_missing_storyboard_id_is_created_and_persisted(monkeypatch):
    saved = {
        "workflow_id": "WF-1",
        "plan_id": "PLAN-1",
        "tasks": [{"id": "TASK-STORYBOARD", "type": "storyboard"}],
    }
    writes = []
    created = {
        "storyboard_id": "STORYBOARD-AUTO",
        "plan_id": "PLAN-1",
        "shots": [{"shot_id": "SHOT-1"}],
    }

    monkeypatch.setattr("core.execution_engine.workflow_engine.load", lambda _wid: saved)
    monkeypatch.setattr("core.execution_engine.workflow_engine.save",
                        lambda data: writes.append(data.copy()) or data)
    monkeypatch.setattr("core.execution_engine.storyboard_director.list", lambda: [])
    monkeypatch.setattr("core.execution_engine.storyboard_director.create_from_plan",
                        lambda plan: created)
    monkeypatch.setattr("core.execution_engine.storyboard_director.load",
                        lambda _sid: created)

    workflow = {"workflow_id": "WF-1", "plan_id": "PLAN-1", "tasks": []}
    task = {"id": "TASK-STORYBOARD", "type": "storyboard"}
    plan = {"plan_id": "PLAN-1", "shots": [{"id": "SHOT-1", "duration": 5}]}

    storyboard_id, storyboard = ExecutionEngine()._ensure_workflow_storyboard(
        "WF-1", workflow, task, plan
    )

    assert storyboard_id == "STORYBOARD-AUTO"
    assert storyboard is created
    assert workflow["storyboard_id"] == "STORYBOARD-AUTO"
    assert task["storyboard_id"] == "STORYBOARD-AUTO"
    assert writes[-1]["storyboard_id"] == "STORYBOARD-AUTO"
    assert writes[-1]["tasks"][0]["storyboard_id"] == "STORYBOARD-AUTO"


def test_missing_storyboard_id_reuses_storyboard_for_same_plan(monkeypatch):
    existing = {
        "storyboard_id": "STORYBOARD-EXISTING",
        "plan_id": "PLAN-1",
        "shots": [{"shot_id": "SHOT-1"}],
    }
    writes = []
    saved = {"workflow_id": "WF-1", "plan_id": "PLAN-1",
             "tasks": [{"id": "TASK-PROMPT", "type": "prompt"}]}
    monkeypatch.setattr("core.execution_engine.workflow_engine.load", lambda _wid: saved)
    monkeypatch.setattr("core.execution_engine.workflow_engine.save",
                        lambda data: writes.append(data.copy()) or data)
    monkeypatch.setattr("core.execution_engine.storyboard_director.list", lambda: [existing])
    monkeypatch.setattr("core.execution_engine.storyboard_director.create_from_plan",
                        lambda _plan: pytest.fail("must reuse storyboard"))
    monkeypatch.setattr("core.execution_engine.storyboard_director.load",
                        lambda _sid: existing)

    workflow = {"workflow_id": "WF-1", "plan_id": "PLAN-1", "tasks": []}
    task = {"id": "TASK-PROMPT", "type": "prompt"}

    storyboard_id, _ = ExecutionEngine()._ensure_workflow_storyboard(
        "WF-1", workflow, task, {"plan_id": "PLAN-1"}
    )

    assert storyboard_id == "STORYBOARD-EXISTING"
    assert writes[-1]["tasks"][0]["storyboard_id"] == "STORYBOARD-EXISTING"


def test_explicit_but_missing_storyboard_is_not_silently_replaced(monkeypatch):
    monkeypatch.setattr("core.execution_engine.storyboard_director.load", lambda _sid: None)
    workflow = {"workflow_id": "WF-1", "plan_id": "PLAN-1", "tasks": []}
    task = {"id": "TASK-PROMPT", "type": "prompt", "storyboard_id": "STORYBOARD-STALE"}

    with pytest.raises(RuntimeError, match="分镜不存在"):
        ExecutionEngine()._ensure_workflow_storyboard(
            "WF-1", workflow, task, {"plan_id": "PLAN-1"}
        )
