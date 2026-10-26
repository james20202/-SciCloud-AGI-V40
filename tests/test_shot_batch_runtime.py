import json

from core.shot_batch import run_shot_batch


def _touch(path):
    path.write_bytes(b"real-enough-test-artifact")
    return str(path)


def test_batch_checkpoints_each_job_and_skips_completed_on_resume(tmp_path):
    manifest = {"jobs": [
        {"job_id": "WF__S1", "shot_id": "S1", "status": "planned", "attempt": 0},
        {"job_id": "WF__S2", "shot_id": "S2", "status": "planned", "attempt": 0},
    ]}
    state = tmp_path / "batch.json"
    first = _touch(tmp_path / "s1.mp4")
    second = _touch(tmp_path / "s2.mp4")
    calls = []

    def render(job):
        calls.append(job["job_id"])
        return [first if job["shot_id"] == "S1" else second]

    result = run_shot_batch(manifest, render, str(state))
    assert result["status"] == "done"
    assert result["progress"] == {"total": 2, "done": 2, "failed": 0, "pending": 0}
    assert len(calls) == 2
    resumed = run_shot_batch(json.loads(state.read_text()), render, str(state))
    assert len(calls) == 2
    assert resumed["progress"]["done"] == 2


def test_batch_records_failure_and_explicit_retry(tmp_path):
    manifest = {"jobs": [{"job_id": "WF__S1", "shot_id": "S1", "status": "planned", "attempt": 0}]}
    state = tmp_path / "batch.json"
    result = run_shot_batch(manifest, lambda job: (_ for _ in ()).throw(RuntimeError("ComfyUI down")), str(state))
    assert result["status"] == "failed"
    assert result["jobs"][0]["status"] == "failed"
    assert result["jobs"][0]["error"] == "ComfyUI down"
    output = _touch(tmp_path / "s1.mp4")
    result = run_shot_batch(json.loads(state.read_text()), lambda job: [output], str(state), retry_failed=True)
    assert result["status"] == "done"
    assert result["jobs"][0]["attempt"] == 2
    assert result["jobs"][0]["outputs"] == [output]


def test_batch_requeues_done_job_if_output_disappears(tmp_path):
    manifest = {"jobs": [{"job_id": "WF__S1", "shot_id": "S1", "status": "done", "attempt": 1, "outputs": [str(tmp_path / "gone.mp4")]}]}
    state = tmp_path / "batch.json"
    output = _touch(tmp_path / "rebuilt.mp4")
    result = run_shot_batch(manifest, lambda job: [output], str(state))
    assert result["status"] == "done"
    assert result["jobs"][0]["attempt"] == 2
    assert result["jobs"][0]["outputs"] == [output]
