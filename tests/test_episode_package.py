import json
import zipfile

import pytest

from core.episode_package import build_episode_package


def _workflow(tmp_path):
    media = tmp_path / "episode.mp4"
    media.write_bytes(b"fake-media-for-package-test")
    prompt = tmp_path / "prompts.json"
    prompt.write_text(json.dumps({"subtitle_srt_draft": "1\n00:00:00,000 --> 00:00:01,000\n测试\n"}), encoding="utf-8")
    qc = tmp_path / "qc.json"
    qc.write_text(json.dumps({"success": True}), encoding="utf-8")
    return {
        "workflow_id": "WF-PACKAGE-TEST",
        "plan_id": "PLAN-TEST",
        "title": "测试剧集",
        "tasks": [
            {"id": "EDIT-1", "type": "edit", "status": "done", "outputs": [str(media)]},
            {"id": "PROMPT-1", "type": "prompt", "status": "done", "outputs": [str(prompt)]},
            {"id": "QC-1", "type": "qc", "status": "done", "outputs": [str(qc)]},
        ],
    }


def test_episode_package_contains_media_subtitle_and_manifest(tmp_path):
    workflow = _workflow(tmp_path)
    output = tmp_path / "package.zip"
    result = build_episode_package(workflow, str(output))
    assert result["success"] is True
    assert result["file_count"] == 3
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert "manifest.json" in names
        assert "subtitles/PROMPT-1_draft.srt" in names
        assert any(name.endswith("episode.mp4") for name in names)
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["workflow_id"] == "WF-PACKAGE-TEST"
        assert all(len(item["sha256"]) == 64 for item in manifest["files"])


def test_episode_package_requires_edit_and_qc_completion(tmp_path):
    workflow = _workflow(tmp_path)
    workflow["tasks"][0]["status"] = "pending"
    with pytest.raises(ValueError, match="最终剪辑"):
        build_episode_package(workflow, str(tmp_path / "bad.zip"))


def test_episode_package_rejects_empty_final_video_output(tmp_path):
    workflow = _workflow(tmp_path)
    empty = tmp_path / "empty.mp4"
    empty.write_bytes(b"")
    workflow["tasks"][0]["outputs"] = [str(empty)]
    # An empty final video must block delivery even when other artifacts are valid.
    with pytest.raises(ValueError, match="最终视频文件"):
        build_episode_package(workflow, str(tmp_path / "with-missing.zip"))


def test_episode_package_rejects_missing_final_video_even_when_other_artifacts_exist(tmp_path):
    workflow = _workflow(tmp_path)
    workflow["tasks"][0]["outputs"] = []
    with pytest.raises(ValueError, match="最终视频文件"):
        build_episode_package(workflow, str(tmp_path / "no-video.zip"))


def test_episode_package_keeps_duplicate_basenames_without_overwriting(tmp_path):
    workflow = _workflow(tmp_path)
    first = tmp_path / "one" / "same.json"
    second = tmp_path / "two" / "same.json"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_text('{"first": true}', encoding="utf-8")
    second.write_text('{"second": true}', encoding="utf-8")
    workflow["tasks"][1]["outputs"] = [str(first), str(second)]
    output = tmp_path / "duplicate-names.zip"
    build_episode_package(workflow, str(output))
    with zipfile.ZipFile(output) as archive:
        artifact_names = [
            name for name in archive.namelist()
            if name.endswith(".json") and name.startswith("artifacts/PROMPT-1/")
        ]
        assert len(artifact_names) == 2
        assert len(set(artifact_names)) == 2


def test_episode_package_rejects_failed_qc_report(tmp_path):
    workflow = _workflow(tmp_path)
    qc = tmp_path / "qc.json"
    qc.write_text(json.dumps({"success": False, "message": "视频流缺失"}), encoding="utf-8")
    workflow["tasks"][2]["outputs"] = [str(qc)]
    with pytest.raises(ValueError, match="质检报告未通过"):
        build_episode_package(workflow, str(tmp_path / "failed-qc.zip"))


def test_episode_package_requires_explicit_successful_qc_report(tmp_path):
    workflow = _workflow(tmp_path)
    qc = tmp_path / "qc.json"
    qc.write_text(json.dumps({"message": "no success field"}), encoding="utf-8")
    workflow["tasks"][2]["outputs"] = [str(qc)]
    with pytest.raises(ValueError, match="明确通过的质检报告"):
        build_episode_package(workflow, str(tmp_path / "unknown-qc.zip"))


def test_episode_package_excludes_outputs_from_failed_and_pending_tasks(tmp_path):
    workflow = _workflow(tmp_path)
    failed_video = tmp_path / "stale-failed-video.mp4"
    pending_asset = tmp_path / "pending-character.json"
    failed_video.write_bytes(b"stale media")
    pending_asset.write_text('{"character":"not ready"}', encoding="utf-8")
    workflow["tasks"].extend([
        {"id": "VIDEO-FAILED", "type": "video", "status": "failed", "outputs": [str(failed_video)]},
        {"id": "CHAR-PENDING", "type": "character", "status": "pending", "outputs": [str(pending_asset)]},
    ])

    output = tmp_path / "completed-only.zip"
    result = build_episode_package(workflow, str(output))

    assert result["success"] is True
    assert result["file_count"] == 3
    assert {item["task_id"] for item in result["manifest"]["ignored_incomplete_task_outputs"]} == {
        "VIDEO-FAILED", "CHAR-PENDING"
    }
    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert not any(name.endswith("stale-failed-video.mp4") for name in names)
        assert not any(name.endswith("pending-character.json") for name in names)
        manifest = json.loads(archive.read("manifest.json"))
        assert len(manifest["ignored_incomplete_task_outputs"]) == 2


@pytest.mark.parametrize("task_type, status", [("edit", "failed"), ("qc", "pending"), ("qc", "failed")])
def test_episode_package_rejects_incomplete_duplicate_final_gate_tasks(tmp_path, task_type, status):
    workflow = _workflow(tmp_path)
    workflow["tasks"].append({
        "id": f"{task_type.upper()}-EXTRA",
        "type": task_type,
        "status": status,
        "outputs": [],
    })
    with pytest.raises(ValueError, match="未完成或失败"):
        build_episode_package(workflow, str(tmp_path / "blocked-package.zip"))


@pytest.mark.parametrize("report", [
    {"success": True, "passed": False, "message": "contradictory report"},
    {"success": False, "passed": True, "message": "contradictory report"},
    {"passed": False, "message": "explicit failure"},
])
def test_episode_package_rejects_qc_reports_with_any_failed_pass_flag(tmp_path, report):
    workflow = _workflow(tmp_path)
    qc = tmp_path / "qc-conflict.json"
    qc.write_text(json.dumps(report), encoding="utf-8")
    workflow["tasks"][2]["outputs"] = [str(qc)]
    with pytest.raises(ValueError, match="质检报告未通过"):
        build_episode_package(workflow, str(tmp_path / "contradictory-qc.zip"))


def test_episode_package_accepts_passed_only_qc_contract(tmp_path):
    workflow = _workflow(tmp_path)
    qc = tmp_path / "qc-passed-only.json"
    qc.write_text(json.dumps({"passed": True, "message": "passed"}), encoding="utf-8")
    workflow["tasks"][2]["outputs"] = [str(qc)]
    result = build_episode_package(workflow, str(tmp_path / "passed-only.zip"))
    assert result["success"] is True
