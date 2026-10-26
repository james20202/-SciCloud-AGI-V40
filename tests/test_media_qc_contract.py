import json
from types import SimpleNamespace

from core.media_quality_engine import MediaQualityEngine
from core.qc_engine import QCEngine


def test_audio_probe_requires_audio_stream_and_finite_duration(tmp_path):
    path = tmp_path / "voice.wav"
    path.write_bytes(b"fixture")
    def runner(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout=json.dumps({
            "format": {"duration": "2.5"},
            "streams": [{"codec_type": "audio", "codec_name": "pcm_s16le"}],
        }), stderr="")
    result = MediaQualityEngine(runner=runner, which=lambda _: True).inspect_audio(str(path), 2.5)
    assert result["passed"] is True
    assert result["has_audio_stream"] is True

    def invalid_runner(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout=json.dumps({
            "format": {"duration": "NaN"},
            "streams": [{"codec_type": "video", "codec_name": "h264"}],
        }), stderr="")
    invalid = MediaQualityEngine(runner=invalid_runner, which=lambda _: True).inspect_audio(str(path))
    assert invalid["passed"] is False
    assert "invalid_duration" in invalid["errors"]
    assert "missing_audio_stream" in invalid["errors"]


def test_video_probe_rejects_missing_video_stream(tmp_path):
    path = tmp_path / "fake.mp4"
    path.write_bytes(b"fixture")
    def runner(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout=json.dumps({
            "format": {"duration": "3"},
            "streams": [{"codec_type": "audio", "codec_name": "aac"}],
        }), stderr="")
    result = MediaQualityEngine(runner=runner, which=lambda name: name == "ffprobe").inspect(str(path))
    assert result["passed"] is False
    assert "missing_video_stream" in result["errors"]


def test_qc_routes_audio_and_video_to_media_quality_engine(tmp_path, monkeypatch):
    import core.qc_engine as module
    video = tmp_path / "video.mp4"
    audio = tmp_path / "voice.wav"
    video.write_bytes(b"video fixture")
    audio.write_bytes(b"audio fixture")
    calls = []
    class FakeMedia:
        def inspect(self, path, expected_duration=None):
            calls.append(("video", path))
            return {"passed": True, "success": True, "message": "video ok"}
        def inspect_audio(self, path, expected_duration=None):
            calls.append(("audio", path))
            return {"passed": False, "success": False, "message": "no audio stream", "errors": ["missing_audio_stream"]}
    monkeypatch.setattr(module, "media_quality_engine", FakeMedia())
    result = QCEngine().inspect_task({}, {"id": "MEDIA-1", "type": "voice", "outputs": [str(video), str(audio)]})
    assert calls == [("video", str(video)), ("audio", str(audio))]
    assert result["success"] is False
    assert result["checks"][0]["success"] is True
    assert result["checks"][1]["success"] is False
    assert "音频技术质检未通过" in result["checks"][1]["message"]


def test_qc_rejects_malformed_output_container_and_failed_workflow(monkeypatch):
    import core.qc_engine as module
    engine = QCEngine()
    malformed = engine.inspect_task({}, {"id": "BAD", "type": "video", "outputs": "episode.mp4"})
    assert malformed["success"] is False
    assert malformed["code"] == "INVALID_OUTPUTS"

    failed_workflow = {"workflow_id": "WF-FAILED", "tasks": [
        {"id": "VIDEO-1", "type": "video", "status": "failed", "name": "视频生成", "error": "render failed"}
    ]}
    monkeypatch.setattr(module, "workflow_engine", type(
        "FakeWorkflowEngine", (), {"load": staticmethod(lambda _wid: failed_workflow)}
    )())
    report = engine.inspect_workflow("WF-FAILED")
    assert report["success"] is False
    assert report["failed_task_id"] == "VIDEO-1"
    assert "render failed" in report["message"]



def test_edit_media_qc_receives_expected_episode_duration(tmp_path, monkeypatch):
    import core.qc_engine as module
    video = tmp_path / "episode.mp4"
    video.write_bytes(b"video fixture")
    calls = []

    class FakeMedia:
        def inspect(self, path, expected_duration=None):
            calls.append((path, expected_duration))
            return {"passed": True, "success": True, "message": "duration checked"}
        def inspect_audio(self, path, expected_duration=None):
            raise AssertionError("edit video should use video probe")

    monkeypatch.setattr(module, "media_quality_engine", FakeMedia())
    result = QCEngine().inspect_task({}, {
        "id": "EDIT-TARGET",
        "type": "edit",
        "expected_duration_seconds": 60,
        "outputs": [str(video)],
    })
    assert result["success"] is True
    assert calls == [(str(video), 60.0)]



def test_video_probe_rejects_duration_mismatch_against_episode_target(tmp_path):
    path = tmp_path / "short_episode.mp4"
    path.write_bytes(b"fixture")

    def runner(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout=json.dumps({
            "format": {"duration": "30", "size": "100"},
            "streams": [{"codec_type": "video", "codec_name": "h264", "width": 720, "height": 1280}],
        }), stderr="")

    result = MediaQualityEngine(runner=runner, which=lambda name: name == "ffprobe").inspect(
        str(path), expected_duration=60
    )
    assert result["passed"] is False
    assert "duration_mismatch" in result["errors"]
    assert result["expected_duration_seconds"] == 60

def test_edit_qc_rejects_silent_final_video_when_audio_sources_exist(tmp_path, monkeypatch):
    import core.qc_engine as module
    video = tmp_path / "episode.mp4"
    voice = tmp_path / "voice.wav"
    video.write_bytes(b"video fixture")
    voice.write_bytes(b"audio fixture")

    class FakeMedia:
        def inspect(self, path, expected_duration=None):
            return {
                "passed": True, "success": True, "message": "video ok",
                "has_video_stream": True, "has_audio_stream": False,
            }
        def inspect_audio(self, path, expected_duration=None):
            return {"passed": True, "success": True, "has_audio_stream": True}

    monkeypatch.setattr(module, "media_quality_engine", FakeMedia())
    workflow = {
        "tasks": [
            {"id": "VOICE", "type": "voice", "status": "done", "outputs": [str(voice)]},
            {"id": "EDIT", "type": "edit", "status": "done", "outputs": [str(video)]},
        ]
    }
    result = QCEngine().inspect_task(workflow, workflow["tasks"][1])

    assert result["success"] is False
    assert result["checks"][0]["success"] is False
    assert "缺少音轨" in result["checks"][0]["message"]

