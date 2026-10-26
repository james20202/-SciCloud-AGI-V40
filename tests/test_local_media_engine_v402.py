import os
import tempfile
from unittest.mock import patch

from core.local_media_engine import LocalMediaEngine


def test_concat_refuses_to_silently_skip_missing_video():
    engine = LocalMediaEngine()
    with tempfile.TemporaryDirectory() as root:
        valid = os.path.join(root, 'valid.mp4')
        with open(valid, 'wb') as f:
            f.write(b'clip')
        result = engine.concat_videos([valid, os.path.join(root, 'missing.mp4')], os.path.join(root, 'out.mp4'))
    assert not result['success']
    assert '拒绝静默跳过' in result['message']


def test_concat_reencodes_when_stream_copy_fails_and_cleans_manifest():
    engine = LocalMediaEngine()
    with tempfile.TemporaryDirectory() as root:
        a = os.path.join(root, 'a.mp4')
        b = os.path.join(root, 'b.mp4')
        out = os.path.join(root, 'out.mp4')
        for p in (a, b):
            with open(p, 'wb') as f:
                f.write(b'clip')
        def fake_run(command, timeout=1800):
            if '-c' in command and 'copy' in command:
                return {'success': False, 'stderr': 'codec mismatch', 'message': '执行失败'}
            with open(out, 'wb') as f:
                f.write(b'valid-output')
            return {'success': True, 'stderr': '', 'message': '执行成功'}
        with patch.object(engine, '_run', side_effect=fake_run):
            result = engine.concat_videos([a, b], out)
        assert result['success']
        assert '兼容编码重制' in result['message']
        assert not os.path.exists(out + '.concat.txt')


def test_image_to_video_validates_duration_and_source():
    engine = LocalMediaEngine()
    with tempfile.TemporaryDirectory() as root:
        out = os.path.join(root, 'clip.mp4')
        result = engine.image_to_video(os.path.join(root, 'missing.png'), out, 5)
        assert not result['success']
        assert '图片不存在' in result['message']
        result = engine.image_to_video('unused.png', out, -1)
        assert not result['success']


def test_export_requires_nonempty_input():
    engine = LocalMediaEngine()
    with tempfile.TemporaryDirectory() as root:
        result = engine.export_mp4(os.path.join(root, 'empty.mp4'), os.path.join(root, 'out.mp4'))
    assert not result['success']
    assert '不存在或为空' in result['message']

def test_media_pipeline_rejects_duplicate_shot_ids(tmp_path):
    import pytest
    from core.media_pipeline import MediaPipeline

    pipeline = MediaPipeline()
    pipeline.root = str(tmp_path)
    with pytest.raises(ValueError, match="镜头 ID 重复"):
        pipeline.create("EP-DUP", [{"id": "SHOT-1"}, {"shot_id": "SHOT-1"}])


def test_media_pipeline_blocks_assembly_until_every_shot_has_video(tmp_path, monkeypatch):
    from core.media_pipeline import MediaPipeline

    pipeline = MediaPipeline()
    pipeline.root = str(tmp_path)
    state = pipeline.create("EP-INCOMPLETE", [{"id": "SHOT-1"}, {"id": "SHOT-2"}])
    video = tmp_path / "shot1.mp4"
    video.write_bytes(b"video")
    assert pipeline.register_artifact(state["pipeline_id"], "SHOT-1", "video", str(video))["success"]
    result = pipeline.assemble(state["pipeline_id"], str(tmp_path / "out.mp4"))
    assert result["success"] is False
    assert result["blocked"] is True
    assert result["missing_shots"] == ["SHOT-2"]
    assert "阻止跳过镜头" in result["message"]


def test_media_pipeline_assembly_uses_all_shots_in_storyboard_order(tmp_path, monkeypatch):
    from core.media_pipeline import MediaPipeline

    pipeline = MediaPipeline()
    pipeline.root = str(tmp_path)
    state = pipeline.create("EP-ORDER", [{"id": "SHOT-1"}, {"id": "SHOT-2"}])
    first, second = tmp_path / "first.mp4", tmp_path / "second.mp4"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    pipeline.register_artifact(state["pipeline_id"], "SHOT-2", "video", str(second))
    pipeline.register_artifact(state["pipeline_id"], "SHOT-1", "video", str(first))
    captured = {}
    monkeypatch.setattr("core.media_pipeline.local_media_engine",
                        __import__("types").SimpleNamespace(concat_videos=lambda paths, output: captured.update(paths=paths) or {"success": True}))
    result = pipeline.assemble(state["pipeline_id"], str(tmp_path / "out.mp4"))
    assert result["success"] is True
    assert captured["paths"] == [str(first.resolve()), str(second.resolve())]


def test_media_pipeline_rejects_unknown_artifact_kind(tmp_path):
    from core.media_pipeline import MediaPipeline

    pipeline = MediaPipeline()
    pipeline.root = str(tmp_path)
    state = pipeline.create("EP-KIND", [{"id": "SHOT-1"}])
    result = pipeline.register_artifact(state["pipeline_id"], "SHOT-1", "made_up", str(tmp_path / "fake"))
    assert result["success"] is False
    assert "不支持的产物类型" in result["message"]
