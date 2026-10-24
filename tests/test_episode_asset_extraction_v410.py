from types import SimpleNamespace

from core.episode_pipeline import EpisodePipeline


def test_create_episode_runs_asset_extraction_and_records_report(tmp_path, monkeypatch):
    plan = {
        "plan_id": "PLAN-INTEGRATION",
        "shots": [{"id": "SHOT-1", "visual_prompt": "moonlit sword", "dialogue": "剑来", "duration": 5}],
        "characters": [{"id": "CHAR-1", "name": "林霄"}],
        "scenes": [{"id": "SCENE-1", "name": "青云山"}],
    }
    monkeypatch.setattr("core.episode_pipeline.episode_engine",
                        SimpleNamespace(create_episode=lambda *a, **k: {
                            "episode_id": "EP-INTEGRATION", "plan_id": "PLAN-INTEGRATION",
                            "workflow_id": "WF-INTEGRATION", "title": "测试集"
                        }))
    monkeypatch.setattr("core.episode_pipeline.director_plan_engine",
                        SimpleNamespace(load_plans=lambda: [plan]))
    report = {"success": True, "created_count": 3, "reused_count": 0,
              "character_count": 1, "scene_count": 1, "shot_card_count": 1}
    monkeypatch.setattr("core.episode_pipeline.script_asset_extractor",
                        SimpleNamespace(extract=lambda p, project_id: report))
    pipeline = EpisodePipeline(project_dir=str(tmp_path))
    result = pipeline.create("一个测试创意", duration=5)
    assert result["asset_extraction"] == report
    assert result["stages"]["plan"]["result"]["asset_extraction"] == report
    assert result["stages"]["plan"]["status"] == "done"
