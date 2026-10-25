from types import SimpleNamespace
import pytest
from core.workflow_engine import WorkflowEngine, STATUS_READY, STATUS_PENDING


def test_workflow_links_storyboard_to_every_task(tmp_path, monkeypatch):
    storyboard = {"storyboard_id": "STORYBOARD-TEST", "shots": []}
    monkeypatch.setattr("core.workflow_engine.storyboard_director",
                        SimpleNamespace(create_from_plan=lambda plan: storyboard))
    engine = WorkflowEngine(project_dir=str(tmp_path))
    plan = {
        "plan_id": "PLAN-TEST", "title": "测试",
        "tasks": [
            {"id": "TASK-1", "type": "story", "name": "剧本"},
            {"id": "TASK-2", "type": "storyboard", "name": "分镜"},
            {"id": "TASK-3", "type": "video", "name": "视频"},
            {"id": "TASK-4", "type": "publish", "name": "发布"},
        ],
    }
    wf = engine.create_from_plan(plan)
    assert wf["storyboard_id"] == "STORYBOARD-TEST"
    assert all(t["storyboard_id"] == "STORYBOARD-TEST" for t in wf["tasks"])
    assert next(t for t in wf["tasks"] if t["id"] == "TASK-1")["status"] == STATUS_READY
    # No character/scene tasks exist in this minimal plan, so storyboard has no unresolved upstream IDs.
    assert next(t for t in wf["tasks"] if t["id"] == "TASK-2")["status"] == STATUS_READY


@pytest.mark.parametrize("plan, message", [
    ({"title": "no id", "tasks": [{"id": "T1", "type": "story"}]}, "plan_id"),
    ({"plan_id": "PLAN-EMPTY", "tasks": []}, "tasks"),
    ({"plan_id": "PLAN-NOID", "tasks": [{"type": "story"}]}, "包含 id"),
    ({"plan_id": "PLAN-DUP", "tasks": [{"id": "T1", "type": "story"}, {"id": "T1", "type": "video"}]}, "重复"),
    ({"plan_id": "PLAN-NOTYPE", "tasks": [{"id": "T1"}]}, "缺少 type"),
])
def test_workflow_rejects_malformed_plan_before_creation(tmp_path, monkeypatch, plan, message):
    monkeypatch.setattr("core.workflow_engine.storyboard_director",
                        SimpleNamespace(create_from_plan=lambda p: pytest.fail("should validate before storyboard creation")))
    engine = WorkflowEngine(project_dir=str(tmp_path))
    with pytest.raises(ValueError, match=message):
        engine.create_from_plan(plan)
    assert list((tmp_path / "workflows").glob("*.json")) == []


def test_empty_workflow_is_not_reported_completed():
    engine = WorkflowEngine(project_dir="/tmp/scicloud-workflow-empty-test")
    wf = {"tasks": [], "paused": False}
    engine._refresh_ready(wf)
    assert wf["status"] == "ready"


def test_dependency_waits_for_every_upstream_task_of_same_type(tmp_path, monkeypatch):
    storyboard = {"storyboard_id": "STORYBOARD-DEPS", "shots": []}
    monkeypatch.setattr("core.workflow_engine.storyboard_director",
                        SimpleNamespace(create_from_plan=lambda plan: storyboard))
    engine = WorkflowEngine(project_dir=str(tmp_path))
    plan = {
        "plan_id": "PLAN-MULTI-STORY", "title": "多段剧本",
        "tasks": [
            {"id": "STORY-1", "type": "story"},
            {"id": "STORY-2", "type": "story"},
            {"id": "CHAR-1", "type": "character"},
            {"id": "SB-1", "type": "storyboard"},
        ],
    }
    wf = engine.create_from_plan(plan)
    by_id = {task["id"]: task for task in wf["tasks"]}
    assert by_id["CHAR-1"]["depends_on"] == ["STORY-1", "STORY-2"]
    assert by_id["SB-1"]["depends_on"] == ["CHAR-1"]
    engine.complete_task(wf["workflow_id"], "STORY-1")
    wf = engine.load(wf["workflow_id"])
    by_id = {task["id"]: task for task in wf["tasks"]}
    assert by_id["STORY-2"]["status"] == STATUS_READY
    assert by_id["CHAR-1"]["status"] == STATUS_PENDING
    engine.complete_task(wf["workflow_id"], "STORY-2")
    wf = engine.load(wf["workflow_id"])
    by_id = {task["id"]: task for task in wf["tasks"]}
    assert by_id["CHAR-1"]["status"] == STATUS_READY
    assert by_id["SB-1"]["status"] == STATUS_PENDING
