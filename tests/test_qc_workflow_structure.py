from core.qc_engine import QCEngine


def test_qc_rejects_completed_task_with_incomplete_sibling_dependency():
    engine = QCEngine()
    workflow = {
        "workflow_id": "WF-QC-DEPENDENCY",
        "storyboard_id": "SB-1",
        "tasks": [
            {"id": "P-1", "type": "prompt", "status": "done", "depends_on": []},
            {"id": "P-2", "type": "prompt", "status": "ready", "depends_on": []},
            {"id": "I-1", "type": "image", "status": "done", "depends_on": ["prompt"]},
        ],
    }

    result = engine._structural_check(workflow)

    assert result["success"] is False
    assert result["code"] == "DEPENDENCY_INCOMPLETE"
    assert result["task_id"] == "I-1"


def test_qc_rejects_mismatched_storyboard_linkage():
    engine = QCEngine()
    workflow = {
        "workflow_id": "WF-QC-LINK",
        "storyboard_id": "SB-1",
        "tasks": [
            {"id": "STORYBOARD", "type": "storyboard", "status": "done", "depends_on": [], "storyboard_id": "SB-2"},
        ],
    }

    result = engine._structural_check(workflow)

    assert result["success"] is False
    assert result["code"] == "STORYBOARD_LINK_MISMATCH"


def test_qc_rejects_duplicate_task_ids():
    engine = QCEngine()
    workflow = {
        "workflow_id": "WF-QC-DUPLICATE",
        "tasks": [
            {"id": "TASK-1", "type": "story", "status": "done", "depends_on": []},
            {"id": "TASK-1", "type": "scene", "status": "ready", "depends_on": []},
        ],
    }

    result = engine._structural_check(workflow)

    assert result["success"] is False
    assert result["code"] == "INVALID_TASK_IDS"


def test_qc_accepts_consistent_workflow_structure():
    engine = QCEngine()
    workflow = {
        "workflow_id": "WF-QC-VALID",
        "storyboard_id": "SB-1",
        "tasks": [
            {"id": "P-1", "type": "prompt", "status": "done", "depends_on": [], "storyboard_id": "SB-1"},
            {"id": "I-1", "type": "image", "status": "done", "depends_on": ["prompt"], "storyboard_id": "SB-1"},
        ],
    }

    result = engine._structural_check(workflow)

    assert result["success"] is True
    assert result["code"] == "STRUCTURE_OK"
