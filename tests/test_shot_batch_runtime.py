import json

from core.shot_batch import load_or_reconcile_shot_batch_manifest, run_shot_batch


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



def test_reconcile_reuses_completed_jobs_only_when_shot_inputs_match(tmp_path):
    state = tmp_path / "batch.json"
    output = _touch(tmp_path / "completed.mp4")
    previous = {
        "status": "failed",
        "jobs": [
            {"job_id": "WF__S1", "shot_id": "S1", "shot_index": 1,
             "duration_seconds": 5, "prompt": "p1", "visual_prompt": "v1",
             "dialogue": "", "voiceover": "", "scene_id": "", "character_ids": [],
             "output_path": "output/shots/WF/S1.mp4", "status": "done",
             "attempt": 1, "outputs": [output]},
            {"job_id": "WF__S2", "shot_id": "S2", "shot_index": 2,
             "duration_seconds": 5, "prompt": "p2", "visual_prompt": "v2",
             "dialogue": "", "voiceover": "", "scene_id": "", "character_ids": [],
             "output_path": "output/shots/WF/S2.mp4", "status": "failed",
             "attempt": 1, "outputs": [], "error": "temporary error"},
        ],
    }
    state.write_text(json.dumps(previous), encoding="utf-8")
    fresh = {
        "workflow_id": "WF", "status": "planned",
        "jobs": [
            {"job_id": "WF__S1", "shot_id": "S1", "shot_index": 1,
             "duration_seconds": 5, "prompt": "p1", "visual_prompt": "v1",
             "dialogue": "", "voiceover": "", "scene_id": "", "character_ids": [],
             "output_path": "output/shots/WF/S1.mp4", "status": "planned",
             "attempt": 0, "outputs": []},
            {"job_id": "WF__S2", "shot_id": "S2", "shot_index": 2,
             "duration_seconds": 5, "prompt": "p2", "visual_prompt": "v2",
             "dialogue": "", "voiceover": "", "scene_id": "", "character_ids": [],
             "output_path": "output/shots/WF/S2.mp4", "status": "planned",
             "attempt": 0, "outputs": []},
        ],
    }
    reconciled = load_or_reconcile_shot_batch_manifest(fresh, str(state))
    assert reconciled["resumed_from_checkpoint"] is True
    assert reconciled["jobs"][0]["status"] == "done"
    assert reconciled["jobs"][0]["outputs"] == [output]
    assert reconciled["jobs"][1]["status"] == "failed"
    assert reconciled["jobs"][1]["attempt"] == 1

    calls = []
    retry_output = _touch(tmp_path / "retry.mp4")
    result = run_shot_batch(
        reconciled,
        lambda job: calls.append(job["job_id"]) or [retry_output],
        str(state),
        retry_failed=True,
    )
    assert calls == ["WF__S2"]
    assert result["status"] == "done"
    assert result["progress"]["done"] == 2


def test_reconcile_discards_checkpoint_if_prompt_changed(tmp_path):
    state = tmp_path / "batch.json"
    state.write_text(json.dumps({"jobs": [{
        "job_id": "WF__S1", "shot_id": "S1", "shot_index": 1,
        "duration_seconds": 5, "prompt": "old", "visual_prompt": "v",
        "dialogue": "", "voiceover": "", "scene_id": "", "character_ids": [],
        "output_path": "output/shots/WF/S1.mp4", "status": "done",
        "attempt": 1, "outputs": [],
    }]}), encoding="utf-8")
    fresh = {"jobs": [{
        "job_id": "WF__S1", "shot_id": "S1", "shot_index": 1,
        "duration_seconds": 5, "prompt": "new", "visual_prompt": "v",
        "dialogue": "", "voiceover": "", "scene_id": "", "character_ids": [],
        "output_path": "output/shots/WF/S1.mp4", "status": "planned",
        "attempt": 0, "outputs": [],
    }]}
    reconciled = load_or_reconcile_shot_batch_manifest(fresh, str(state))
    assert "resumed_from_checkpoint" not in reconciled
    assert reconciled["jobs"][0]["status"] == "planned"
    assert reconciled["jobs"][0]["prompt"] == "new"
