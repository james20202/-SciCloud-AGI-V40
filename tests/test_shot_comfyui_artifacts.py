import tempfile
from unittest.mock import patch

from core.shot_production_engine import ShotProductionEngine


def test_queued_or_empty_comfy_result_does_not_mark_shot_done():
    with tempfile.TemporaryDirectory() as root:
        engine = ShotProductionEngine()
        engine.root = root
        run = engine.create_run('EP-TEST', [{'shot_id': 'SHOT-1', 'comfy_workflow': {'1': {}}}])
        with patch('core.shot_production_engine.production_engine.submit_comfy',
                   return_value={'success': True, 'outputs': [], 'message': 'queued'}):
            result = engine.produce_shot(run['run_id'], 'SHOT-1')
        assert result['status'] == 'blocked'
        assert result['done_count'] == 0
        assert result['blocked_count'] == 1


def test_existing_video_is_accepted_without_image_or_comfy_workflow(tmp_path):
    video = tmp_path / "already-rendered.mp4"
    video.write_bytes(b"existing-video")
    engine = ShotProductionEngine()
    engine.root = str(tmp_path / "runs")
    run = engine.create_run("EP-TEST", [{
        "shot_id": "SHOT-VIDEO-ONLY",
        "video_path": str(video),
        "video_path_required": True,
        "visual_prompt": "主角在青云山巅拔剑",
    }])

    result = engine.produce_shot(run["run_id"], "SHOT-VIDEO-ONLY")

    assert result["status"] == "completed"
    assert result["done_count"] == 1
    shot = engine.load(run["run_id"])["shots"][0]
    assert any(item["kind"] == "video" and item["path"] == str(video.resolve())
               for item in shot["artifacts"])
    assert "existing_video" in shot["last_result"]["steps"]


def test_missing_existing_video_does_not_bypass_media_generation(tmp_path):
    engine = ShotProductionEngine()
    engine.root = str(tmp_path / "runs")
    run = engine.create_run("EP-TEST", [{
        "shot_id": "SHOT-MISSING-VIDEO",
        "video_path": str(tmp_path / "missing.mp4"),
        "video_path_required": True,
    }])

    result = engine.produce_shot(run["run_id"], "SHOT-MISSING-VIDEO")

    assert result["status"] == "blocked"
    assert result["done_count"] == 0
