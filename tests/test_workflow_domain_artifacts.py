import json
import os

import core.execution_engine as execution_module


class FakeWorkflowEngine:
    def __init__(self, workflow):
        self.workflow = workflow

    def load(self, workflow_id):
        assert workflow_id == self.workflow["workflow_id"]
        return self.workflow

    def start_task(self, workflow_id, task_id):
        next(t for t in self.workflow["tasks"] if t["id"] == task_id)["status"] = "running"
        return self.workflow

    def save(self, workflow):
        self.workflow = workflow

    def complete_task(self, workflow_id, task_id):
        next(t for t in self.workflow["tasks"] if t["id"] == task_id)["status"] = "done"
        return self.workflow

    def fail_task(self, workflow_id, task_id, error):
        task = next(t for t in self.workflow["tasks"] if t["id"] == task_id)
        task["status"], task["error"] = "failed", error
        return self.workflow


class FakeSkillRegistry:
    def get(self, skill_id):
        return {"enabled": True}


class FakeModelHub:
    def find_for_skill(self, *args):
        return None


class FakeAssetManager:
    def register_execution(self, task, outputs, project_id=None, data=None):
        return [{"asset_path": outputs[0]}]

    def register_plan_entity(self, entity, kind, plan_id):
        return {"entity": entity["id"], "kind": kind}


class FakePlanEngine:
    def load_plans(self):
        return [{
            "plan_id": "PLAN-TEST",
            "title": "Test",
            "idea": "修仙故事",
            "story": {"logline": "故事大纲"},
            "intent": {"duration_seconds": 60},
        }]


class FakeStoryboardDirector:
    def __init__(self, root, shots=None):
        self.root = root
        self.shots = [{"id": "S1"}, {"id": "S2"}] if shots is None else shots
        os.makedirs(root, exist_ok=True)
        self.path = os.path.join(root, "STORYBOARD-TEST.json")
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"storyboard_id": "STORYBOARD-TEST", "shots": self.shots}, f)

    def load(self, storyboard_id):
        if storyboard_id != "STORYBOARD-TEST":
            return None
        with open(self.path, encoding="utf-8") as f:
            return json.load(f)

    def _path(self, storyboard_id):
        return self.path

    def build_prompt(self, storyboard_id, index, plan=None, model="generic"):
        return {"prompt_id": f"P-{index}", "prompt": f"镜头 {index + 1} 的提示词"}


def setup_engine(monkeypatch, tmp_path, task_type):
    task = {
        "id": "TASK-04" if task_type == "storyboard" else "TASK-05",
        "type": task_type,
        "status": "ready",
        "storyboard_id": "STORYBOARD-TEST",
    }
    workflow = {
        "workflow_id": "WF-TEST",
        "plan_id": "PLAN-TEST",
        "storyboard_id": "STORYBOARD-TEST",
        "tasks": [task],
    }
    monkeypatch.setattr(execution_module, "workflow_engine", FakeWorkflowEngine(workflow))
    monkeypatch.setattr(execution_module, "skill_registry", FakeSkillRegistry())
    monkeypatch.setattr(execution_module, "model_hub", FakeModelHub())
    monkeypatch.setattr(execution_module, "asset_manager", FakeAssetManager())
    monkeypatch.setattr(execution_module, "director_plan_engine", FakePlanEngine())
    monkeypatch.setattr(execution_module, "storyboard_director", FakeStoryboardDirector(str(tmp_path / "storyboards")))
    monkeypatch.setattr(execution_module, "PROJECT_DIR", str(tmp_path))
    return execution_module.ExecutionEngine(), workflow


def test_storyboard_task_verifies_and_registers_actual_storyboard(monkeypatch, tmp_path):
    engine, workflow = setup_engine(monkeypatch, tmp_path, "storyboard")

    result = engine.execute("WF-TEST", "TASK-04")

    assert result["success"] is True
    assert result["data"]["storyboard_id"] == "STORYBOARD-TEST"
    assert result["data"]["shot_count"] == 2
    assert os.path.isfile(result["outputs"][0])
    assert workflow["tasks"][0]["status"] == "done"
    assert workflow["tasks"][0]["result"]["storyboard_id"] == "STORYBOARD-TEST"


def test_prompt_task_generates_one_prompt_per_storyboard_shot(monkeypatch, tmp_path):
    engine, workflow = setup_engine(monkeypatch, tmp_path, "prompt")

    result = engine.execute("WF-TEST", "TASK-05")

    assert result["success"] is True
    assert result["data"]["prompt_count"] == 2
    payload = json.loads(open(result["outputs"][0], encoding="utf-8").read())
    assert [x["prompt"] for x in payload["prompts"]] == ["镜头 1 的提示词", "镜头 2 的提示词"]
    assert workflow["tasks"][0]["status"] == "done"


def test_storyboard_task_failure_marks_task_failed(monkeypatch, tmp_path):
    engine, workflow = setup_engine(monkeypatch, tmp_path, "storyboard")
    monkeypatch.setattr(execution_module, "storyboard_director", FakeStoryboardDirector(str(tmp_path / "empty"), shots=[]))

    result = engine.execute("WF-TEST", "TASK-04")

    assert result["success"] is False
    assert "不存在或没有镜头" in result["message"]
    assert workflow["tasks"][0]["status"] == "failed"
    assert workflow["tasks"][0]["error"] == result["message"]



class FakeAdapterResult:
    def __init__(self, outputs, success=True):
        self.success = success
        self.message = "adapter reported success"
        self.outputs = outputs
        self.data = {"adapter": "fake"}

    def to_dict(self):
        return {
            "success": self.success,
            "message": self.message,
            "outputs": self.outputs,
            "data": self.data,
        }


class FakeMediaAdapter:
    def __init__(self, outputs, success=True):
        self.result = FakeAdapterResult(outputs, success)

    def execute(self, model, task, context):
        return self.result


class FakeMediaModelHub(FakeModelHub):
    def find_for_skill(self, *args):
        return {"model_id": "MODEL-FAKE", "adapter": "fake", "enabled": True}


def test_media_task_does_not_complete_when_adapter_produces_no_file(monkeypatch, tmp_path):
    engine, workflow = setup_engine(monkeypatch, tmp_path, "image")
    monkeypatch.setattr(execution_module, "model_hub", FakeMediaModelHub())
    monkeypatch.setattr(execution_module, "ADAPTERS", {"fake": FakeMediaAdapter(outputs=[])})

    result = engine.execute("WF-TEST", "TASK-05")

    assert result["success"] is False
    assert "没有生成可验证" in result["message"]
    assert workflow["tasks"][0]["status"] == "failed"
    assert workflow["tasks"][0]["outputs"] == []


def test_media_task_completes_when_adapter_output_is_a_nonempty_file(monkeypatch, tmp_path):
    engine, workflow = setup_engine(monkeypatch, tmp_path, "image")
    media_path = tmp_path / "generated.png"
    media_path.write_bytes(b"valid-test-media")
    monkeypatch.setattr(execution_module, "model_hub", FakeMediaModelHub())
    monkeypatch.setattr(execution_module, "ADAPTERS", {"fake": FakeMediaAdapter(outputs=[str(media_path)])})

    result = engine.execute("WF-TEST", "TASK-05")

    assert result["success"] is True
    assert result["outputs"] == [str(media_path)]
    assert workflow["tasks"][0]["status"] == "done"



def test_artifact_paths_are_sanitized_and_json_writes_are_valid(monkeypatch, tmp_path):
    engine, _ = setup_engine(monkeypatch, tmp_path, "storyboard")

    path = engine._artifact(
        {"workflow_id": "../../outside"},
        {"id": "../../escape"},
        "prompt/../artifact",
        {"safe": True},
    )

    execution_root = (tmp_path / "execution").resolve()
    assert os.path.commonpath([str(execution_root), os.path.abspath(path)]) == str(execution_root)
    with open(path, encoding="utf-8") as f:
        assert json.load(f) == {"safe": True}


class RaisingMediaAdapter:
    def execute(self, model, task, context):
        raise RuntimeError("simulated adapter crash")


def test_adapter_exception_marks_task_failed_not_running(monkeypatch, tmp_path):
    engine, workflow = setup_engine(monkeypatch, tmp_path, "image")
    monkeypatch.setattr(execution_module, "model_hub", FakeMediaModelHub())
    monkeypatch.setattr(execution_module, "ADAPTERS", {"fake": RaisingMediaAdapter()})

    result = engine.execute("WF-TEST", "TASK-05")

    assert result["success"] is False
    assert "simulated adapter crash" in result["message"]
    assert workflow["tasks"][0]["status"] == "failed"


def test_paused_workflow_does_not_execute_task(monkeypatch, tmp_path):
    engine, workflow = setup_engine(monkeypatch, tmp_path, "image")
    workflow["paused"] = True
    monkeypatch.setattr(
        execution_module.workflow_engine,
        "start_task",
        lambda workflow_id, task_id: workflow,
    )
    monkeypatch.setattr(execution_module, "model_hub", FakeMediaModelHub())
    adapter = FakeMediaAdapter(outputs=[])
    monkeypatch.setattr(execution_module, "ADAPTERS", {"fake": adapter})

    result = engine.execute("WF-TEST", "TASK-05")

    assert result["success"] is False
    assert "已暂停" in result["message"]
    assert workflow["tasks"][0]["status"] == "ready"
