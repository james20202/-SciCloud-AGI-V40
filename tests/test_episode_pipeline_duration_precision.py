from types import SimpleNamespace

from core.episode_pipeline import EpisodePipeline


def test_create_pipeline_preserves_canonical_fractional_duration(tmp_path, monkeypatch):
    episode = {
        "episode_id": "EP-DURATION",
        "plan_id": "PLAN-DURATION",
        "workflow_id": "WF-DURATION",
        "title": "小数时长测试",
        "duration_seconds": 37.2,
    }
    plan = {"plan_id": "PLAN-DURATION", "shots": [{"id": "SHOT-1"}]}

    monkeypatch.setattr(
        "core.episode_pipeline.episode_engine",
        SimpleNamespace(create_episode=lambda *args, **kwargs: episode),
    )
    monkeypatch.setattr(
        "core.episode_pipeline.director_plan_engine",
        SimpleNamespace(load_plans=lambda: [plan]),
    )
    monkeypatch.setattr(
        "core.episode_pipeline.script_asset_extractor",
        SimpleNamespace(extract=lambda *args, **kwargs: {"success": True, "assets": []}),
    )

    pipeline = EpisodePipeline(project_dir=str(tmp_path))
    record = pipeline.create("测试创意", duration=37.29)

    assert record["duration_seconds"] == 37.2
    assert pipeline.load("EP-DURATION")["duration_seconds"] == 37.2


def test_create_pipeline_uses_requested_duration_for_legacy_episode_record(tmp_path, monkeypatch):
    episode = {
        "episode_id": "EP-LEGACY",
        "plan_id": "PLAN-LEGACY",
        "workflow_id": "WF-LEGACY",
        "title": "兼容测试",
    }
    plan = {"plan_id": "PLAN-LEGACY", "shots": [{"id": "SHOT-1"}]}

    monkeypatch.setattr(
        "core.episode_pipeline.episode_engine",
        SimpleNamespace(create_episode=lambda *args, **kwargs: episode),
    )
    monkeypatch.setattr(
        "core.episode_pipeline.director_plan_engine",
        SimpleNamespace(load_plans=lambda: [plan]),
    )
    monkeypatch.setattr(
        "core.episode_pipeline.script_asset_extractor",
        SimpleNamespace(extract=lambda *args, **kwargs: {"success": True, "assets": []}),
    )

    record = EpisodePipeline(project_dir=str(tmp_path)).create("测试创意", duration=59.5)

    assert record["duration_seconds"] == 59.5
