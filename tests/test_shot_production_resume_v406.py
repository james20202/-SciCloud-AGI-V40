import json
from core.shot_production_engine import ShotProductionEngine


def test_done_shot_reuses_valid_artifact_without_repeating_generation(tmp_path, monkeypatch):
    engine = ShotProductionEngine()
    engine.root = str(tmp_path / "runs")
    import os
    os.makedirs(engine.root)
    artifact = tmp_path / "image.png"
    artifact.write_bytes(b"image")
    run = engine.create_run("EP-1", [{"shot_id": "S1", "image_path": str(artifact), "visual_prompt": "stable"}])
    result = engine.produce_shot(run["run_id"], "S1")
    assert result["done_count"] == 1
    attempts = result["shots"][0]["attempts"]
    reused = engine.produce_shot(run["run_id"], "S1")
    assert reused["shots"][0]["attempts"] == attempts
    assert reused["done_count"] == 1


def test_missing_completed_artifact_is_queued_again(tmp_path):
    import os
    engine = ShotProductionEngine()
    engine.root = str(tmp_path / "runs")
    os.makedirs(engine.root)
    artifact = tmp_path / "image.png"
    artifact.write_bytes(b"image")
    run = engine.create_run("EP-1", [{"shot_id": "S1", "image_path": str(artifact)}])
    done = engine.produce_shot(run["run_id"], "S1")
    assert done["done_count"] == 1
    artifact.unlink()
    status = engine.status(run["run_id"])
    assert status["ready_count"] == 1
    assert status["done_count"] == 0


def test_prompt_change_invalidates_completed_shot_cache(tmp_path):
    import os
    engine = ShotProductionEngine()
    engine.root = str(tmp_path / "runs")
    os.makedirs(engine.root)
    artifact = tmp_path / "image.png"
    artifact.write_bytes(b"image")
    run = engine.create_run("EP-1", [{"shot_id": "S1", "image_path": str(artifact), "visual_prompt": "one"}])
    engine.produce_shot(run["run_id"], "S1")
    saved = engine.load(run["run_id"])
    saved["shots"][0]["spec"]["visual_prompt"] = "two"
    engine._save(saved)
    status = engine.status(run["run_id"])
    assert status["ready_count"] == 1
    assert status["done_count"] == 0
