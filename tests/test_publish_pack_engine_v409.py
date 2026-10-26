import json
import os
import zipfile
from core.publish_pack_engine import PublishPackEngine


def _setup(tmp_path, monkeypatch, qc_report=None):
    import core.publish_pack_engine as module
    project = tmp_path / "project"
    output = tmp_path / "output"
    episodes = project / "episodes"
    episodes.mkdir(parents=True)
    episode = episodes / "EP-TEST.json"
    episode.write_text(json.dumps({"episode_id": "EP-TEST", "duration_seconds": 30}), encoding="utf-8")
    video = tmp_path / "episode.mp4"
    video.write_bytes(b"fake-video")
    monkeypatch.setattr(module, "PROJECT_DIR", str(project))
    monkeypatch.setattr(module, "OUTPUT_DIR", str(output))
    class FakeQC:
        def inspect(self, path, expected_duration=None):
            assert path == str(video)
            assert expected_duration == 30
            return qc_report if qc_report is not None else {"passed": True, "success": True}
    monkeypatch.setattr(module, "media_quality_engine", FakeQC())
    return project, output, video


def test_publish_pack_rejects_missing_final_video(tmp_path, monkeypatch):
    project, output, video = _setup(tmp_path, monkeypatch)
    result = PublishPackEngine().build("EP-TEST", str(tmp_path / "missing.mp4"))
    assert result["success"] is False
    assert "最终视频不存在或为空" in result["message"]
    assert not output.exists()


def test_publish_pack_rejects_empty_final_video(tmp_path, monkeypatch):
    project, output, video = _setup(tmp_path, monkeypatch)
    empty = tmp_path / "empty.mp4"
    empty.write_bytes(b"")
    result = PublishPackEngine().build("EP-TEST", str(empty))
    assert result["success"] is False
    assert "最终视频不存在或为空" in result["message"]
    assert not output.exists()


def test_publish_pack_rejects_failed_final_media_qc(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, {"passed": False, "errors": ["missing_video_stream"]})
    result = PublishPackEngine().build("EP-TEST", str(tmp_path / "episode.mp4"))
    assert result["success"] is False
    assert "未通过发布前媒体质检" in result["message"]
    assert result["quality_report"]["errors"] == ["missing_video_stream"]


def test_publish_pack_contains_video_and_verified_manifest_after_qc(tmp_path, monkeypatch):
    project, output, video = _setup(tmp_path, monkeypatch)
    result = PublishPackEngine().build("EP-TEST", str(video))
    assert result["success"] is True
    assert os.path.isfile(result["package"])
    with zipfile.ZipFile(result["package"]) as archive:
        names = archive.namelist()
        assert "episode.mp4" in names
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["final_video"] == "episode.mp4"
        assert any(item["filename"] == "episode.mp4" and len(item["sha256"]) == 64
                   for item in manifest["assets"])
