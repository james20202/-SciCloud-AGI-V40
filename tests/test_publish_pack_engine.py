import hashlib
import json
import zipfile

from core.publish_pack_engine import PublishPackEngine


def test_publish_pack_rejects_requested_missing_or_empty_video(tmp_path, monkeypatch):
    import core.publish_pack_engine as module

    project_dir = tmp_path / "projects"
    output_dir = tmp_path / "output"
    (project_dir / "episodes").mkdir(parents=True)
    (project_dir / "episodes" / "EP-TEST.json").write_text('{"episode_id":"EP-TEST"}', encoding="utf-8")
    monkeypatch.setattr(module, "PROJECT_DIR", str(project_dir))
    monkeypatch.setattr(module, "OUTPUT_DIR", str(output_dir))

    missing = tmp_path / "missing.mp4"
    result = PublishPackEngine().build("EP-TEST", final_video=str(missing))

    assert result["success"] is False
    assert "最终视频不存在或为空" in result["message"]
    assert not (output_dir / "EP-TEST_publish.zip").exists()

    empty = tmp_path / "empty.mp4"
    empty.write_bytes(b"")
    result = PublishPackEngine().build("EP-TEST", final_video=str(empty))
    assert result["success"] is False
    assert not (output_dir / "EP-TEST_publish.zip").exists()


def test_publish_pack_manifest_tracks_final_video_checksum(tmp_path, monkeypatch):
    import core.publish_pack_engine as module

    project_dir = tmp_path / "projects"
    output_dir = tmp_path / "output"
    (project_dir / "episodes").mkdir(parents=True)
    (project_dir / "episodes" / "EP-TEST.json").write_text('{"episode_id":"EP-TEST"}', encoding="utf-8")
    video = tmp_path / "final.mp4"
    video_bytes = b"fake-mp4-content-for-unit-test"
    video.write_bytes(video_bytes)
    monkeypatch.setattr(module, "PROJECT_DIR", str(project_dir))
    monkeypatch.setattr(module, "OUTPUT_DIR", str(output_dir))

    result = PublishPackEngine().build("EP-TEST", final_video=str(video))

    assert result["success"] is True
    assert result["manifest"]["final_video"] == "final.mp4"
    asset = next(a for a in result["manifest"]["assets"] if a["filename"] == "final.mp4")
    assert asset["sha256"] == hashlib.sha256(video_bytes).hexdigest()
    with zipfile.ZipFile(result["package"]) as archive:
        assert "final.mp4" in archive.namelist()
        assert "manifest.json" in archive.namelist()
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["final_video"] == "final.mp4"
