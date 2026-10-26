import copy
import os

import pytest

import core.shot_production_engine as shot_module
from core.shot_production_engine import ShotProductionEngine


class FailingJobStore:
    def __init__(self, stale):
        self.stale = stale

    def get(self, run_id):
        return {"status": "ready", "result": copy.deepcopy(self.stale)}

    def __setitem__(self, key, value):
        raise OSError("simulated SQLite commit failure")


def test_load_prefers_newer_json_snapshot_if_sqlite_commit_failed(tmp_path, monkeypatch):
    engine = ShotProductionEngine()
    engine.root = str(tmp_path / "runs")
    os.makedirs(engine.root)
    created = engine.create_run("EP-1", [{"shot_id": "S1"}])
    stale = copy.deepcopy(engine.load(created["run_id"]))
    stale["updated_at"] = "2000-01-01T00:00:00.000000"
    monkeypatch.setattr(shot_module, "_job_store", FailingJobStore(stale))

    newer = copy.deepcopy(stale)
    newer["message"] = "new JSON snapshot"
    with pytest.raises(OSError, match="SQLite commit failure"):
        engine._save(newer)

    recovered = engine.load(created["run_id"])
    assert recovered["message"] == "new JSON snapshot"
    assert recovered["updated_at"] > stale["updated_at"]


def test_load_falls_back_to_sqlite_when_json_snapshot_is_corrupt(tmp_path, monkeypatch):
    engine = ShotProductionEngine()
    engine.root = str(tmp_path / "runs")
    os.makedirs(engine.root)
    created = engine.create_run("EP-1", [{"shot_id": "S1"}])
    stored = engine.load(created["run_id"])
    path = engine._path(created["run_id"])
    with open(path, "w", encoding="utf-8") as stream:
        stream.write("{invalid json")

    recovered = engine.load(created["run_id"])
    assert recovered["run_id"] == stored["run_id"]
    assert recovered["shots"][0]["shot_id"] == "S1"
