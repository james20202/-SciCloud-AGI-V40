import json
import zipfile

import pytest

from core.episode_package import build_episode_package


def _workflow(tmp_path):
    media = tmp_path / "episode.mp4"
    media.write_bytes(b"fake-media-for-package-test")
    prompt = tmp_path / "prompts.json"
    prompt.write_text(json.dumps({"subtitle_srt_draft": "1\\n00:00:00,000 --> 00:00:01,000\\n测试\\n"}), encoding="utf-8")
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


def test_episode_package_rejects_empty_outputs(tmp_path):
    workflow = _workflow(tmp_path)
    empty = tmp_path / "empty.mp4"
    empty.write_bytes(b"")
    workflow["tasks"][0]["outputs"] = [str(empty)]
    # Other artifacts remain valid and can be packaged, but the empty media is reported.
    result = build_episode_package(workflow, str(tmp_path / "with-missing.zip"))
    assert str(empty) in result["missing_or_invalid_outputs"]
