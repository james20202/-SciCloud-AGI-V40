from types import SimpleNamespace
from core.episode_pipeline import EpisodePipeline


def test_prepare_shots_preserves_director_shot_ids(tmp_path, monkeypatch):
    plan = {"plan_id": "PLAN-ABC", "shots": [{"id": "SHOT-ORIGINAL", "visual_prompt": "moonlit temple"}]}
    captured = {}
    monkeypatch.setattr("core.episode_pipeline.director_plan_engine",
                        SimpleNamespace(load_plans=lambda: [plan]))
    monkeypatch.setattr("core.episode_pipeline.shot_production_engine",
                        SimpleNamespace(create_run=lambda eid, shots: captured.update(eid=eid, shots=shots) or {"run_id": "RUN-1", "shots": shots}))
    pipeline = EpisodePipeline(project_dir=str(tmp_path))
    pipeline._save({"episode_id": "EP-ABC", "plan_id": "PLAN-ABC", "stage": "plan",
                    "stages": {stage: {"status": "pending", "result": None} for stage in pipeline.STAGES},
                    "shot_run_id": None})
    result = pipeline.prepare_shots("EP-ABC")
    assert result["shot_run_id"] == "RUN-1"
    assert captured["shots"][0]["shot_id"] == "SHOT-ORIGINAL"
    assert captured["shots"][0]["visual_prompt"] == "moonlit temple"


def test_run_media_stops_cleanly_if_shot_preparation_fails(tmp_path, monkeypatch):
    pipeline = EpisodePipeline(project_dir=str(tmp_path))
    pipeline._save({"episode_id": "EP-FAIL", "plan_id": "PLAN-MISSING", "stage": "plan",
                    "stages": {stage: {"status": "pending", "result": None} for stage in pipeline.STAGES},
                    "shot_run_id": None})
    monkeypatch.setattr(pipeline, "prepare_shots", lambda eid: {"success": False, "message": "plan missing"})
    result = pipeline.run_media("EP-FAIL")
    assert result["status"] == "blocked"
    assert result["stages"]["shots"]["result"]["message"] == "plan missing"
