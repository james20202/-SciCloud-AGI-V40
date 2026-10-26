from types import SimpleNamespace

import pytest

from core.episode_engine import EpisodeEngine


@pytest.mark.parametrize("duration", [7.5, 37.2, 59.5, 73.3, 60])
def test_create_episode_uses_canonical_plan_duration(tmp_path, monkeypatch, duration):
    plan = {
        "plan_id": "PLAN-TEST1234",
        "title": "测试短剧",
        "intent": {"duration_seconds": round(float(duration), 1)},
    }
    monkeypatch.setattr(
        "core.episode_engine.director_plan_engine",
        SimpleNamespace(create_plan=lambda *args, **kwargs: plan),
    )
    monkeypatch.setattr(
        "core.episode_engine.workflow_engine",
        SimpleNamespace(create_from_plan=lambda received: {"workflow_id": "WF-TEST"}),
    )

    engine = EpisodeEngine(project_dir=str(tmp_path))
    episode = engine.create_episode("测试创意", duration=duration)

    assert episode["duration_seconds"] == round(float(duration), 1)
    assert engine.load(episode["episode_id"])["duration_seconds"] == round(float(duration), 1)


def test_create_episode_does_not_store_unvalidated_input_over_plan_duration(tmp_path, monkeypatch):
    plan = {
        "plan_id": "PLAN-TEST5678",
        "title": "测试短剧",
        "intent": {"duration_seconds": 12.4},
    }
    monkeypatch.setattr(
        "core.episode_engine.director_plan_engine",
        SimpleNamespace(create_plan=lambda *args, **kwargs: plan),
    )
    monkeypatch.setattr(
        "core.episode_engine.workflow_engine",
        SimpleNamespace(create_from_plan=lambda received: {"workflow_id": "WF-TEST"}),
    )

    episode = EpisodeEngine(project_dir=str(tmp_path)).create_episode("测试创意", duration=12.49)

    assert episode["duration_seconds"] == 12.4
