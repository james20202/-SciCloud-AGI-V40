from types import SimpleNamespace
import pytest
from core.workflow_engine import WorkflowEngine, STATUS_READY, STATUS_PENDING


def test_workflow_links_storyboard_to_every_task(tmp_path, monkeypatch):
    storyboard = {"storyboard_id": "STORYBOARD-TEST", "shots": [{"shot_id": "SHOT-1", "duration": 5, "visual_prompt": "测试镜头"}]}
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
    assert next(t for t in wf["tasks"] if t["id"] == "TASK-2")["status"] == STATUS_PENDING
    assert next(t for t in wf["tasks"] if t["id"] == "TASK-2")["depends_on_task_ids"] == []


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


def test_workflow_rejects_empty_storyboard_before_persisting(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "core.workflow_engine.storyboard_director",
        SimpleNamespace(create_from_plan=lambda plan: {"storyboard_id": "STORYBOARD-EMPTY", "shots": []}),
    )
    engine = WorkflowEngine(project_dir=str(tmp_path))
    plan = {"plan_id": "PLAN-EMPTY-STORYBOARD", "tasks": [{"id": "TASK-1", "type": "story"}]}

    with pytest.raises(ValueError, match="分镜没有有效镜头"):
        engine.create_from_plan(plan)
    assert list((tmp_path / "workflows").glob("*.json")) == []



def test_workflow_persists_exact_upstream_task_ids(tmp_path, monkeypatch):
    storyboard = {
        "storyboard_id": "STORYBOARD-TASK-IDS",
        "shots": [{"id": "SHOT-1", "duration": 5, "visual_prompt": "测试镜头"}],
    }
    monkeypatch.setattr(
        "core.workflow_engine.storyboard_director",
        SimpleNamespace(create_from_plan=lambda plan: storyboard),
    )
    engine = WorkflowEngine(project_dir=str(tmp_path))
    plan = {
        "plan_id": "PLAN-TASK-IDS",
        "title": "重复上游任务",
        "tasks": [
            {"id": "STORY-1", "type": "story"},
            {"id": "STORY-2", "type": "story"},
            {"id": "CHAR-1", "type": "character"},
            {"id": "SCENE-1", "type": "scene"},
            {"id": "SB-1", "type": "storyboard"},
        ],
    }

    workflow = engine.create_from_plan(plan)
    by_id = {task["id"]: task for task in workflow["tasks"]}

    assert by_id["CHAR-1"]["depends_on_task_ids"] == ["STORY-1", "STORY-2"]
    assert by_id["SCENE-1"]["depends_on_task_ids"] == ["STORY-1", "STORY-2"]
    assert by_id["SB-1"]["depends_on_task_ids"] == ["CHAR-1", "SCENE-1"]
    assert by_id["SB-1"]["status"] == STATUS_PENDING

    engine.complete_task(workflow["workflow_id"], "STORY-1")
    workflow = engine.load(workflow["workflow_id"])
    by_id = {task["id"]: task for task in workflow["tasks"]}
    assert by_id["CHAR-1"]["status"] == STATUS_PENDING
    assert by_id["SCENE-1"]["status"] == STATUS_PENDING

    engine.complete_task(workflow["workflow_id"], "STORY-2")
    workflow = engine.load(workflow["workflow_id"])
    by_id = {task["id"]: task for task in workflow["tasks"]}
    assert by_id["CHAR-1"]["status"] == STATUS_READY
    assert by_id["SCENE-1"]["status"] == STATUS_READY
    assert by_id["SB-1"]["status"] == STATUS_PENDING
