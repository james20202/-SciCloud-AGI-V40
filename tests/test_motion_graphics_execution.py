import os
from copy import deepcopy

import core.execution_engine as execution_module


class FakeWorkflowEngine:
    def __init__(self, workflow):
        self.workflow = deepcopy(workflow)

    def load(self, _wid):
        return deepcopy(self.workflow)

    def start_task(self, _wid, task_id):
        task = next(t for t in self.workflow["tasks"] if t["id"] == task_id)
        task["status"] = "running"
        return deepcopy(self.workflow)

    def save(self, workflow):
        self.workflow = deepcopy(workflow)

    def complete_task(self, _wid, task_id):
        next(t for t in self.workflow["tasks"] if t["id"] == task_id)["status"] = "done"

    def fail_task(self, _wid, task_id, message):
        task = next(t for t in self.workflow["tasks"] if t["id"] == task_id)
        task.update(status="failed", error=message)


class FakeSkillRegistry:
    def get(self, _skill_id):
        return {"enabled": True}


class FakeAssetManager:
    def register_execution(self, task, outputs, project_id=None, data=None):
        return [{"path": outputs[0], "project_id": project_id}]


class FakeMotionGraphics:
    def render_card(self, **kwargs):
        output = kwargs["output_video"]
        os.makedirs(os.path.dirname(output), exist_ok=True)
        with open(output, "wb") as handle:
            handle.write(b"fake-mp4")
        return {"success": True, "output": output, "duration_seconds": kwargs["duration_seconds"]}


def setup(monkeypatch, tmp_path, task_type="title_card", renderer=None):
    workflow = {
        "workflow_id": "WF-1",
        "plan_id": "PLAN-1",
        "tasks": [{
            "id": "CARD-1", "type": task_type, "status": "ready",
            "title": "第一章：青云初现", "subtitle": "仙路初启",
            "duration_seconds": 3, "aspect_ratio": "9:16", "style": "xianxia",
        }],
    }
    fake_workflow = FakeWorkflowEngine(workflow)
    monkeypatch.setattr(execution_module, "workflow_engine", fake_workflow)
    monkeypatch.setattr(execution_module, "skill_registry", FakeSkillRegistry())
    monkeypatch.setattr(execution_module, "asset_manager", FakeAssetManager())
    monkeypatch.setattr(execution_module, "motion_graphics_engine", renderer or FakeMotionGraphics())
    monkeypatch.setattr(execution_module, "PROJECT_DIR", str(tmp_path))
    return fake_workflow


def test_title_card_task_renders_and_registers_media(monkeypatch, tmp_path):
    workflow = setup(monkeypatch, tmp_path)
    result = execution_module.ExecutionEngine().execute("WF-1", "CARD-1")
    assert result["success"] is True
    assert result["outputs"]
    assert os.path.getsize(result["outputs"][0]) > 0
    saved = next(t for t in workflow.workflow["tasks"] if t["id"] == "CARD-1")
    assert saved["status"] == "done"
    assert saved["outputs"] == result["outputs"]
    assert result["assets"]


def test_motion_graphics_task_fails_when_renderer_fails(monkeypatch, tmp_path):
    class FailedRenderer:
        def render_card(self, **_kwargs):
            return {"success": False, "message": "FFmpeg missing"}

    workflow = setup(monkeypatch, tmp_path, task_type="motion_graphics", renderer=FailedRenderer())
    result = execution_module.ExecutionEngine().execute("WF-1", "CARD-1")
    assert result["success"] is False
    assert "FFmpeg missing" in result["message"]
    saved = next(t for t in workflow.workflow["tasks"] if t["id"] == "CARD-1")
    assert saved["status"] == "failed"
