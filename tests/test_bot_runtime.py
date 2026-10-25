import json

import pytest

from core.bot_runtime import BotRuntime


def test_publish_dispatches_to_matching_handlers_and_persists_completion(tmp_path):
    log_path = tmp_path / "bot-events.jsonl"
    runtime = BotRuntime(str(log_path))
    seen = []
    runtime.subscribe("workflow.ready", lambda event: seen.append(event["payload"]["workflow_id"]) or "queued")

    result = runtime.publish("workflow.ready", {"workflow_id": "WF-001"}, event_id="evt-001")

    assert result["success"] is True
    assert result["handled"] == 1
    assert seen == ["WF-001"]
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert any(row["record_type"] == "event_completed" and row["event_id"] == "evt-001" for row in records)


def test_completed_event_is_not_dispatched_again_after_restart(tmp_path):
    log_path = tmp_path / "bot-events.jsonl"
    first = BotRuntime(str(log_path))
    first.subscribe("asset.created", lambda event: "indexed")
    assert first.publish("asset.created", {"asset_id": "A-1"}, event_id="evt-asset")["success"]

    second = BotRuntime(str(log_path))
    seen = []
    second.subscribe("asset.created", lambda event: seen.append(event["event_id"]))
    result = second.publish("asset.created", {"asset_id": "A-1"}, event_id="evt-asset")

    assert result["success"] is True
    assert result["duplicate"] is True
    assert seen == []


def test_missing_subscriber_is_visible_and_not_marked_completed(tmp_path):
    log_path = tmp_path / "bot-events.jsonl"
    runtime = BotRuntime(str(log_path))

    result = runtime.publish("unknown.event", {}, event_id="evt-unknown")

    assert result["success"] is False
    assert "没有 Bot 订阅" in result["message"]
    assert "evt-unknown" not in runtime._completed_ids


def test_handler_failure_is_reported_and_event_can_be_retried(tmp_path):
    runtime = BotRuntime(str(tmp_path / "bot-events.jsonl"))
    attempts = []

    def flaky_handler(event):
        attempts.append(event["event_id"])
        if len(attempts) == 1:
            raise RuntimeError("temporary failure")
        return "ok"

    runtime.subscribe("qc.failed", flaky_handler)
    first = runtime.publish("qc.failed", {"workflow_id": "WF-2"}, event_id="evt-retry")
    second = runtime.publish("qc.failed", {"workflow_id": "WF-2"}, event_id="evt-retry")

    assert first["success"] is False
    assert first["errors"][0]["error"] == "temporary failure"
    assert second["success"] is True
    assert attempts == ["evt-retry", "evt-retry"]


def test_payload_must_be_json_serializable_before_handler_runs():
    runtime = BotRuntime()
    seen = []
    runtime.subscribe("test.event", lambda event: seen.append(event))

    with pytest.raises((TypeError, ValueError)):
        runtime.publish("test.event", {"not_json": object()})

    assert seen == []
