from copy import deepcopy

from core.shot_retry_policy import prepare_retry, retryable_shot_ids


def test_retry_only_failed_and_blocked_shots_preserves_successes():
    run = {"shots": [
        {"shot_id": "A", "status": "done", "artifacts": [{"path": "/good.png"}]},
        {"shot_id": "B", "status": "failed", "artifacts": [{"path": "/partial.png"}]},
        {"shot_id": "C", "status": "blocked", "artifacts": []},
    ]}
    before_good = deepcopy(run["shots"][0])
    result = prepare_retry(run)
    assert result["retry_shot_ids"] == ["B", "C"]
    assert run["shots"][0] == before_good
    assert run["shots"][1]["status"] == "ready"
    assert run["shots"][1]["artifacts"] == []
    assert result["retry_count"] == 2


def test_requested_retry_ids_are_intersected_with_retryable_statuses():
    run = {"shots": [{"shot_id": "A", "status": "done"},
                     {"shot_id": "B", "status": "failed"},
                     {"shot_id": "C", "status": "blocked"}]}
    assert retryable_shot_ids(run, ["A", "B"]) == ["B"]
