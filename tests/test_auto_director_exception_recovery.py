from copy import deepcopy

import core.auto_director as auto_director_module
from core.auto_director import AutoDirector


class FakeEngine:
    def __init__(self):
        self.workflow = {
            "workflow_id": "WF-CRASH",
            "status": "ready",
            "paused": False,
            "tasks": [{"id": "TASK-CRASH", "type": "video", "status": "ready"}],
        }
        self.failed = []

    def load(self, workflow_id):
        return deepcopy(self.workflow)

    def fail_task(self, workflow_id, task_id, error):
        self.failed.append((workflow_id, task_id, error))
        self.workflow["tasks"][0]["status"] = "failed"
        self.workflow["tasks"][0]["error"] = error
        self.workflow["status"] = "failed"


class CrashingExecutor:
    def execute(self, workflow_id, task_id):
        raise RuntimeError("simulated adapter crash")


def test_auto_director_marks_crashed_task_failed_and_returns_recoverable_result(tmp_path, monkeypatch):
    monkeypatch.setattr(auto_director_module, "PROJECT_DIR", str(tmp_path))
    engine = FakeEngine()
    director = AutoDirector(engine=engine, executor=CrashingExecutor())

    result = director.run("WF-CRASH", max_steps=1, delay=0)

    assert result["success"] is False
    assert result["stopped"] is True
    task_result = result["results"][0]["result"]
    assert task_result["recoverable"] is True
    assert "simulated adapter crash" in task_result["message"]
    assert engine.failed
    assert engine.workflow["tasks"][0]["status"] == "failed"
