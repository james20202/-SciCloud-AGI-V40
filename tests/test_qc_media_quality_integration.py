import os

from core.qc_engine import QCEngine


class FakeMediaQualityEngine:
    def __init__(self, result):
        self.result = result
        self.checked = []

    def inspect(self, path):
        self.checked.append(path)
        return dict(self.result)


class FakeVisionQC:
    def analyze(self, path, context=None):
        return {"success": True, "semantic_checked": False, "message": "not enabled"}


def test_video_outputs_are_checked_by_media_quality_engine(tmp_path, monkeypatch):
    import core.qc_engine as module

    video = tmp_path / "episode.mp4"
    video.write_bytes(b"non-empty fixture")
    media = FakeMediaQualityEngine({
        "success": True,
        "passed": True,
        "message": "基础媒体质检通过",
        "errors": [],
        "duration_seconds": 12.0,
        "has_video_stream": True,
    })
    monkeypatch.setattr(module, "media_quality_engine", media)
    monkeypatch.setattr(module, "vision_qc", FakeVisionQC())

    report = QCEngine().inspect_task(
        {"workflow_id": "WF-1"},
        {"id": "TASK-VIDEO", "type": "video", "outputs": [str(video)]},
    )

    assert report["success"] is True
    assert media.checked == [str(video)]
    assert report["media_quality"][0]["passed"] is True
    assert report["checks"][0]["media_quality"]["has_video_stream"] is True


def test_video_media_quality_failure_fails_task_qc(tmp_path, monkeypatch):
    import core.qc_engine as module

    video = tmp_path / "broken.mp4"
    video.write_bytes(b"not a real video")
    media = FakeMediaQualityEngine({
        "success": False,
        "passed": False,
        "message": "ffprobe 失败",
        "errors": ["probe_failed"],
    })
    monkeypatch.setattr(module, "media_quality_engine", media)

    report = QCEngine().inspect_task(
        {"workflow_id": "WF-2"},
        {"id": "TASK-BROKEN", "type": "video", "outputs": [str(video)]},
    )

    assert report["success"] is False
    assert report["code"] == "INVALID_OUTPUT"
    assert report["media_quality"][0]["errors"] == ["probe_failed"]
    assert "媒体技术质检未通过" in report["checks"][0]["message"]


def test_non_video_json_outputs_do_not_call_media_quality(tmp_path, monkeypatch):
    import json
    import core.qc_engine as module

    artifact = tmp_path / "storyboard.json"
    artifact.write_text(json.dumps({"shots": []}), encoding="utf-8")
    media = FakeMediaQualityEngine({"success": True, "passed": True})
    monkeypatch.setattr(module, "media_quality_engine", media)

    report = QCEngine().inspect_task(
        {"workflow_id": "WF-3"},
        {"id": "TASK-STORYBOARD", "type": "storyboard", "outputs": [str(artifact)]},
    )

    assert report["success"] is True
    assert media.checked == []
    assert report["media_quality"] == []
