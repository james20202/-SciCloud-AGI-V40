import json
import os

import pytest

from core.shot_production_engine import ShotProductionEngine


def test_create_run_rejects_duplicate_shot_ids(tmp_path):
    engine = ShotProductionEngine()
    engine.root = str(tmp_path / "runs")
    with pytest.raises(ValueError, match="shot_id 重复"):
        engine.create_run("EP-1", [{"shot_id": "S1"}, {"shot_id": "S1"}])
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("run_id", ["../escape", "nested/run", r"nested\\run", "bad\x00id", ".", ".."])
def test_run_path_rejects_unsafe_identifiers(tmp_path, run_id):
    engine = ShotProductionEngine()
    engine.root = str(tmp_path / "runs")
    with pytest.raises(ValueError, match="run_id"):
        engine._path(run_id)


@pytest.mark.parametrize("episode_id", ["", "../escape", "nested/episode", "bad\x00id"])
def test_create_run_rejects_unsafe_episode_ids(tmp_path, episode_id):
    engine = ShotProductionEngine()
    engine.root = str(tmp_path / "runs")
    with pytest.raises(ValueError, match="episode_id"):
        engine.create_run(episode_id, [{"shot_id": "S1"}])
    assert list(tmp_path.iterdir()) == []


def test_failed_snapshot_write_preserves_previous_file_and_cleans_temp(tmp_path, monkeypatch):
    engine = ShotProductionEngine()
    engine.root = str(tmp_path / "runs")
    os.makedirs(engine.root)
    run = engine.create_run("EP-1", [{"shot_id": "S1"}])
    path = engine._path(run["run_id"])
    original = open(path, encoding="utf-8").read()
    data = engine.load(run["run_id"])
    data["message"] = "new state"

    def fail_dump(*args, **kwargs):
        raise OSError("simulated disk write failure")

    monkeypatch.setattr(json, "dump", fail_dump)
    with pytest.raises(OSError, match="simulated disk write failure"):
        engine._save(data)

    assert open(path, encoding="utf-8").read() == original
    assert not [name for name in os.listdir(engine.root) if name.endswith(".tmp")]
