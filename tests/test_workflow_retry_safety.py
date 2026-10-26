import json
import pytest

from core.workflow_engine import STATUS_DONE, STATUS_FAILED, STATUS_PENDING, STATUS_READY, STATUS_RUNNING, WorkflowEngine


def _engine(tmp_path):
    return WorkflowEngine(project_dir=str(tmp_path))


def test_retry_invalidates_downstream_stages_and_stale_outputs(tmp_path):
    engine = _engine(tmp_path)
    workflow = {
        "workflow_id": "WF-RETRY-TEST",
        "paused": False,
        "tasks": [
            {"id": "STORY-1", "type": "story", "status": STATUS_FAILED, "depends_on": [], "outputs": ["old-script.json"], "error": "previous failure"},
            {"id": "STORY-2", "type": "story", "status": STATUS_DONE, "depends_on": [], "outputs": ["old-script-2.json"]},
            {"id": "PROMPT-1", "type": "prompt", "status": STATUS_DONE, "depends_on": ["story"], "outputs": ["old-prompts.json"], "result": {"stale": True}},
            {"id": "IMAGE-1", "type": "image", "status": STATUS_DONE, "depends_on": ["prompt"], "outputs": ["old-image.png"]},
            {"id": "PUBLISH-1", "type": "publish", "status": STATUS_DONE, "depends_on": ["image"], "outputs": ["old-release.zip"]},
        ],
    }
    engine.save(workflow)

    updated = engine.retry_task("WF-RETRY-TEST", "STORY-1")
    persisted = engine.load("WF-RETRY-TEST")
    by_id = {task["id"]: task for task in persisted["tasks"]}

    assert by_id["STORY-1"]["status"] == STATUS_READY
    for task_id in ("STORY-1", "STORY-2", "PROMPT-1", "IMAGE-1", "PUBLISH-1"):
        assert by_id[task_id]["outputs"] == []
        assert by_id[task_id]["progress"] == 0
    assert "result" not in by_id["PROMPT-1"]
    assert by_id["PROMPT-1"]["status"] == STATUS_PENDING
    assert by_id["IMAGE-1"]["status"] == STATUS_PENDING
    assert by_id["PUBLISH-1"]["status"] == STATUS_PENDING
    assert set(updated["retry_invalidated_task_ids"]) == {"STORY-1", "STORY-2", "PROMPT-1", "IMAGE-1", "PUBLISH-1"}


@pytest.mark.parametrize("bad_id", ["../escape", "nested/workflow", r"nested\workflow", "bad\x00id", "", ".."])
def test_workflow_path_rejects_unsafe_ids(tmp_path, bad_id):
    engine = _engine(tmp_path)
    with pytest.raises(ValueError):
        engine._path(bad_id)


def test_workflow_save_uses_valid_json_and_no_temporary_file_remains(tmp_path):
    engine = _engine(tmp_path)
    workflow = {"workflow_id": "WF-ATOMIC-SAVE", "tasks": [], "paused": False}

    path = engine.save(workflow)

    with open(path, encoding="utf-8") as handle:
        loaded = json.load(handle)
    assert loaded["workflow_id"] == "WF-ATOMIC-SAVE"
    assert not [name for name in (tmp_path / "workflows").iterdir() if name.name.endswith(".tmp")]


def test_qc_cannot_be_manually_completed_without_passed_report(tmp_path):
    engine = _engine(tmp_path)
    engine.save({
        "workflow_id": "WF-QC-GATE",
        "paused": False,
        "tasks": [
            {"id": "QC-1", "type": "qc", "status": STATUS_READY, "depends_on": [], "outputs": []},
            {"id": "PUB-1", "type": "publish", "status": STATUS_PENDING, "depends_on": ["qc"], "outputs": []},
        ],
    })

    updated = engine.complete_task("WF-QC-GATE", "QC-1")
    persisted = engine.load("WF-QC-GATE")
    qc = next(task for task in persisted["tasks"] if task["id"] == "QC-1")
    publish = next(task for task in persisted["tasks"] if task["id"] == "PUB-1")

    assert qc["status"] == STATUS_READY
    assert "真实 QC" in qc["error"]
    assert publish["status"] == STATUS_PENDING


def test_publish_cannot_start_when_qc_was_marked_done_without_report(tmp_path):
    engine = _engine(tmp_path)
    engine.save({
        "workflow_id": "WF-PUBLISH-GATE",
        "paused": False,
        "tasks": [
            {"id": "QC-1", "type": "qc", "status": STATUS_DONE, "depends_on": [], "outputs": []},
            {"id": "PUB-1", "type": "publish", "status": STATUS_READY, "depends_on": ["qc"], "outputs": []},
        ],
    })

    engine.start_task("WF-PUBLISH-GATE", "PUB-1")
    persisted = engine.load("WF-PUBLISH-GATE")
    publish = next(task for task in persisted["tasks"] if task["id"] == "PUB-1")

    assert publish["status"] == STATUS_READY
    assert "QC 报告" in publish["error"]


def test_passed_qc_artifact_is_required_and_allows_publish_start(tmp_path):
    engine = _engine(tmp_path)
    report_path = tmp_path / "qc-report.json"
    report_path.write_text(json.dumps({"success": True, "passed": True}), encoding="utf-8")
    engine.save({
        "workflow_id": "WF-PUBLISH-PASS",
        "paused": False,
        "tasks": [
            {"id": "QC-1", "type": "qc", "status": STATUS_READY, "depends_on": [], "outputs": [str(report_path)]},
            {"id": "PUB-1", "type": "publish", "status": STATUS_PENDING, "depends_on": ["qc"], "outputs": []},
        ],
    })

    engine.complete_task("WF-PUBLISH-PASS", "QC-1")
    engine.start_task("WF-PUBLISH-PASS", "PUB-1")
    persisted = engine.load("WF-PUBLISH-PASS")
    qc = next(task for task in persisted["tasks"] if task["id"] == "QC-1")
    publish = next(task for task in persisted["tasks"] if task["id"] == "PUB-1")

    assert qc["status"] == STATUS_DONE
    assert publish["status"] == STATUS_RUNNING
    assert publish["error"] is None


def test_publish_cannot_be_manually_completed_without_real_package(tmp_path):
    engine = _engine(tmp_path)
    engine.save({
        "workflow_id": "WF-PUBLISH-COMPLETE-GATE",
        "paused": False,
        "tasks": [
            {"id": "PUB-1", "type": "publish", "status": STATUS_READY, "depends_on": [], "outputs": []},
        ],
    })

    engine.complete_task("WF-PUBLISH-COMPLETE-GATE", "PUB-1")
    persisted = engine.load("WF-PUBLISH-COMPLETE-GATE")
    publish = persisted["tasks"][0]

    assert publish["status"] == STATUS_READY
    assert "非空交付包" in publish["error"]
