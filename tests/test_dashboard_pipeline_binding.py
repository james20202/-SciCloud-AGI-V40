import os
import tempfile
from types import SimpleNamespace

from core.episode_pipeline import EpisodePipeline


def test_episode_pipeline_binds_exact_plan_not_latest_sorted_plan(monkeypatch, tmp_path):
    wanted = {
        "plan_id": "PLAN-ABCD1234", "title": "正确项目",
        "shots": [{"id": "SHOT-1", "duration": 60}]
    }
    unrelated = {
        "plan_id": "PLAN-ZZZZ9999", "title": "其他项目",
        "shots": [{"id": "SHOT-X", "duration": 10}]
    }
    fake_episode = {
        "episode_id": "EP-ABCD1234", "plan_id": wanted["plan_id"],
        "workflow_id": "WF-ABCD1234", "title": wanted["title"]
    }
    monkeypatch.setattr("core.episode_pipeline.episode_engine",
                        SimpleNamespace(create_episode=lambda *a, **k: fake_episode))
    monkeypatch.setattr("core.episode_pipeline.director_plan_engine",
                        SimpleNamespace(load_plans=lambda: [unrelated, wanted]))
    pipeline = EpisodePipeline(project_dir=str(tmp_path))
    result = pipeline.create("本次测试创意", duration=60)
    assert result["plan_id"] == wanted["plan_id"]
    assert result["stages"]["plan"]["result"]["plan_id"] == wanted["plan_id"]
    assert result["stages"]["plan"]["result"]["shot_count"] == 1
