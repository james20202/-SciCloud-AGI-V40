import json
import os

from core.execution_engine import ExecutionEngine
from core.workflow_engine import WorkflowEngine


def test_publish_task_creates_package_and_completes(tmp_path, monkeypatch):
    import core.execution_engine as execution_module

    project_dir = tmp_path / "project"
    engine = WorkflowEngine(project_dir=str(project_dir))
    media = tmp_path / "episode.mp4"
    media.write_bytes(b"verified-test-media")
    qc_report = tmp_path / "qc.json"
    qc_report.write_text(json.dumps({"success": True}), encoding="utf-8")
    workflow = {
        "workflow_id": "WF-PUBLISH-TEST",
        "plan_id": "PLAN-PUBLISH-TEST",
        "title": "发布测试",
        "storyboard_id": "STORYBOARD-TEST",
        "paused": False,
        "tasks": [
            {"id": "EDIT-1", "type": "edit", "status": "done", "progress": 100, "depends_on": [], "outputs": [str(media)]},
            {"id": "QC-1", "type": "qc", "status": "done", "progress": 100, "depends_on": ["edit"], "outputs": [str(qc_report)]},
            {"id": "PUBLISH-1", "type": "publish", "status": "ready", "progress": 0, "depends_on": ["qc"], "outputs": []},
        ],
    }
    engine.save(workflow)
    monkeypatch.setattr(execution_module, "workflow_engine", engine)
    monkeypatch.setattr(execution_module, "PROJECT_DIR", str(project_dir))
    monkeypatch.setattr(execution_module.skill_registry, "get", lambda _skill_id: {"enabled": True})
    monkeypatch.setattr(execution_module.asset_manager, "register_execution", lambda *args, **kwargs: [])
    result = ExecutionEngine().execute("WF-PUBLISH-TEST", "PUBLISH-1")

    assert result["success"] is True
    assert os.path.isfile(result["outputs"][0])
    final_workflow = engine.load("WF-PUBLISH-TEST")
    publish_task = next(task for task in final_workflow["tasks"] if task["id"] == "PUBLISH-1")
    assert publish_task["status"] == "done"
    assert publish_task["outputs"] == result["outputs"]
