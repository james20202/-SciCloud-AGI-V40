import os
from core.persistent_job_store import PersistentJobStore
from core.shot_production_engine import ShotProductionEngine, _job_store


def test_sqlite_job_store_survives_close_and_reopen(tmp_path):
    db = tmp_path / "jobs.sqlite3"
    store = PersistentJobStore(str(db))
    store["JOB-1"] = {
        "kind": "shot_run", "status": "running", "progress": 25,
        "message": "rendering", "result": {"shot_id": "S1", "nested": {"ok": True}},
        "params": {"episode_id": "EP-1"},
    }
    store.close()
    reopened = PersistentJobStore(str(db))
    job = reopened.get("JOB-1")
    assert job["status"] == "running"
    assert job["result"]["nested"]["ok"] is True
    assert job["params"]["episode_id"] == "EP-1"
    assert job["progress"] == 25
    reopened.close()


def test_interrupted_sqlite_jobs_are_recoverable(tmp_path):
    db = tmp_path / "jobs.sqlite3"
    store = PersistentJobStore(str(db))
    store["JOB-2"] = {"kind": "shot_run", "status": "running", "result": {"shots": []}}
    store.close()
    reopened = PersistentJobStore(str(db))
    recovered = reopened.recover_interrupted_jobs()
    assert recovered == ["JOB-2"]
    assert reopened["JOB-2"]["status"] == "interrupted"
    assert "exited" in reopened["JOB-2"]["message"]
    reopened.close()


def test_shot_run_is_written_to_sqlite_and_json(tmp_path):
    engine = ShotProductionEngine()
    engine.root = str(tmp_path / "runs")
    os.makedirs(engine.root)
    run = engine.create_run("EP-DB", [{"shot_id": "S1", "visual_prompt": "moonlit mountain"}])
    assert os.path.isfile(os.path.join(engine.root, run["run_id"] + ".json"))
    record = _job_store.get(run["run_id"])
    assert record["kind"] == "shot_run"
    assert record["result"]["shots"][0]["shot_id"] == "S1"
    assert record["params"]["episode_id"] == "EP-DB"


def test_interrupted_shot_is_requeued_on_load(tmp_path):
    engine = ShotProductionEngine()
    engine.root = str(tmp_path / "runs")
    os.makedirs(engine.root)
    run = engine.create_run("EP-RECOVER", [{"shot_id": "S1", "visual_prompt": "lightning"}])
    saved = engine.load(run["run_id"])
    saved["status"] = "running"
    saved["shots"][0]["status"] = "running"
    engine._save(saved)
    record = dict(_job_store[run["run_id"]])
    record["status"] = "interrupted"
    _job_store[run["run_id"]] = record
    recovered = engine.load(run["run_id"])
    assert recovered["shots"][0]["status"] == "ready"
    assert "已恢复" in recovered["shots"][0]["last_result"]["message"]
    assert _job_store[run["run_id"]]["status"] == "ready"
