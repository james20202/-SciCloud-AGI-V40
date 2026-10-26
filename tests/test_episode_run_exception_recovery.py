import json

import pytest

import core.episode_engine as episode_module
from core.episode_engine import EpisodeEngine


def test_episode_run_persists_unexpected_director_exception(tmp_path, monkeypatch):
    engine = EpisodeEngine(project_dir=str(tmp_path))
    episode = {
        "episode_id": "EP-EXCEPTION",
        "workflow_id": "WF-EXCEPTION",
        "title": "test",
        "status": "planned",
        "attempt": 0,
        "last_result": None,
    }
    engine._save(episode)

    def crash(*args, **kwargs):
        raise RuntimeError("simulated executor crash")

    monkeypatch.setattr(episode_module.auto_director, "run", crash)
    monkeypatch.setattr(
        episode_module.workflow_engine,
        "load",
        lambda workflow_id: {
            "workflow_id": workflow_id,
            "status": "ready",
            "paused": False,
            "tasks": [{"id": "TASK-1", "status": "ready", "progress": 0}],
        },
    )
    result = engine.run("EP-EXCEPTION")

    assert result["status"] == "blocked"
    assert result["attempt"] == 1
    assert result["last_result"]["success"] is False
    assert "simulated executor crash" in result["last_result"]["message"]
    saved = json.loads((tmp_path / "episodes" / "EP-EXCEPTION.json").read_text(encoding="utf-8"))
    assert saved["last_result"]["recoverable"] is True


@pytest.mark.parametrize("limit", [0, -1, 1001, "bad", 1.5, True])
def test_episode_run_rejects_invalid_step_limit(tmp_path, limit):
    engine = EpisodeEngine(project_dir=str(tmp_path))
    engine._save({
        "episode_id": "EP-LIMIT",
        "workflow_id": "WF-LIMIT",
        "title": "test",
        "status": "planned",
        "attempt": 0,
    })
    with pytest.raises(ValueError, match="max_steps"):
        engine.run("EP-LIMIT", max_steps=limit)
