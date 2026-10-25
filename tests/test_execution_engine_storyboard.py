import json
from datetime import datetime
from core.execution_engine import ExecutionEngine


class FakeWorkflowEngine:
    def __init__(self, workflow):
        self.workflow = workflow

    def load(self, workflow_id):
        return self.workflow

    def start_task(self, workflow_id, task_id):
        next(t for t in self.workflow["tasks"] if t["id"] == task_id)["status"] = "running"
        return self.workflow

    def complete_task(self, workflow_id, task_id):
        next(t for t in self.workflow["tasks"] if t["id"] == task_id)["status"] = "done"
        return self.workflow

    def fail_task(self, workflow_id, task_id, error):
        task = next(t for t in self.workflow["tasks"] if t["id"] == task_id)
        task["status"] = "failed"
        task["error"] = error
        return self.workflow

    def save(self, workflow):
        return None


def test_storyboard_task_writes_real_storyboard_payload(tmp_path, monkeypatch):
    import core.execution_engine as module

    storyboard = {
        "storyboard_id": "STORYBOARD-REAL",
        "plan_id": "PLAN-REAL",
        "title": "测试分镜",
        "shots": [
            {"id": "SHOT-1", "duration": 4.5, "visual_prompt": "仙剑出鞘", "dialogue": "接招！"},
            {"id": "SHOT-2", "duration": 5.5, "visual_prompt": "剑气破空", "dialogue": ""},
        ],
    }
    task = {"id": "TASK-SB", "type": "storyboard", "status": "ready", "storyboard_id": "STORYBOARD-REAL"}
    workflow = {"workflow_id": "WF-REAL", "plan_id": "PLAN-REAL", "title": "测试分镜",
                "storyboard_id": "STORYBOARD-REAL", "tasks": [task]}
    fake_engine = FakeWorkflowEngine(workflow)
    monkeypatch.setattr(module, "workflow_engine", fake_engine)
    monkeypatch.setattr(module, "storyboard_director", type("Director", (), {"load": lambda self, sid: storyboard})())
    monkeypatch.setattr(module, "skill_registry", type("Skills", (), {"get": lambda self, sid: {"enabled": True}})())
    monkeypatch.setattr(module, "model_hub", type("Models", (), {"find_for_skill": lambda self, *args: None})())
    monkeypatch.setattr(module, "asset_manager", type("Assets", (), {"register_execution": lambda self, *args, **kwargs: []})())
    monkeypatch.setattr(module, "PROJECT_DIR", str(tmp_path))

    result = ExecutionEngine().execute("WF-REAL", "TASK-SB")

    assert result["success"] is True
    assert task["status"] == "done"
    assert len(result["outputs"]) == 1
    with open(result["outputs"][0], encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["storyboard_id"] == "STORYBOARD-REAL"
    assert payload["shot_count"] == 2
    assert payload["duration_seconds"] == 10.0
    assert payload["storyboard"]["shots"][0]["visual_prompt"] == "仙剑出鞘"
    assert payload["storyboard"]["shots"][0]["dialogue"] == "接招！"


def test_storyboard_task_fails_when_storyboard_asset_missing(tmp_path, monkeypatch):
    import core.execution_engine as module

    task = {"id": "TASK-SB", "type": "storyboard", "status": "ready", "storyboard_id": "STORYBOARD-MISSING"}
    workflow = {"workflow_id": "WF-MISSING", "plan_id": "PLAN-MISSING",
                "storyboard_id": "STORYBOARD-MISSING", "tasks": [task]}
    fake_engine = FakeWorkflowEngine(workflow)
    monkeypatch.setattr(module, "workflow_engine", fake_engine)
    monkeypatch.setattr(module, "storyboard_director", type("Director", (), {"load": lambda self, sid: None})())
    monkeypatch.setattr(module, "skill_registry", type("Skills", (), {"get": lambda self, sid: {"enabled": True}})())
    monkeypatch.setattr(module, "model_hub", type("Models", (), {"find_for_skill": lambda self, *args: None})())
    monkeypatch.setattr(module, "PROJECT_DIR", str(tmp_path))

    result = ExecutionEngine().execute("WF-MISSING", "TASK-SB")

    assert result["success"] is False
    assert task["status"] == "failed"
    assert "分镜资产不存在" in task["error"]
    assert not list(tmp_path.rglob("*storyboard*.json"))
