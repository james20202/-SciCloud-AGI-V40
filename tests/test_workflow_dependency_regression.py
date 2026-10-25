from core.workflow_engine import STATUS_DONE, STATUS_PENDING, STATUS_READY, WorkflowEngine


def test_stage_dependency_waits_for_every_task_of_same_type(tmp_path):
    engine = WorkflowEngine(project_dir=str(tmp_path))
    workflow = {
        "workflow_id": "WF-DEPENDENCY-TEST",
        "paused": False,
        "tasks": [
            {"id": "PROMPT-1", "type": "prompt", "status": STATUS_DONE, "depends_on": []},
            {"id": "PROMPT-2", "type": "prompt", "status": STATUS_READY, "depends_on": []},
            {"id": "IMAGE-1", "type": "image", "status": STATUS_READY, "depends_on": ["prompt"]},
        ],
    }

    engine._refresh_ready(workflow)

    assert workflow["tasks"][2]["status"] == STATUS_PENDING


def test_stage_dependency_unlocks_after_all_sibling_tasks_complete(tmp_path):
    engine = WorkflowEngine(project_dir=str(tmp_path))
    workflow = {
        "workflow_id": "WF-DEPENDENCY-TEST",
        "paused": False,
        "tasks": [
            {"id": "PROMPT-1", "type": "prompt", "status": STATUS_DONE, "depends_on": []},
            {"id": "PROMPT-2", "type": "prompt", "status": STATUS_DONE, "depends_on": []},
            {"id": "IMAGE-1", "type": "image", "status": STATUS_PENDING, "depends_on": ["prompt"]},
        ],
    }

    engine._refresh_ready(workflow)

    assert workflow["tasks"][2]["status"] == STATUS_READY


def test_stale_ready_task_is_reblocked_when_dependency_becomes_incomplete(tmp_path):
    engine = WorkflowEngine(project_dir=str(tmp_path))
    workflow = {
        "workflow_id": "WF-DEPENDENCY-TEST",
        "paused": False,
        "tasks": [
            {"id": "PROMPT-1", "type": "prompt", "status": STATUS_PENDING, "depends_on": []},
            {"id": "IMAGE-1", "type": "image", "status": STATUS_READY, "depends_on": ["prompt"]},
        ],
    }

    engine._refresh_ready(workflow)

    assert workflow["tasks"][1]["status"] == STATUS_PENDING
