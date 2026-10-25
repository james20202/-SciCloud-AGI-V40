from core.workflow_engine import WorkflowEngine, STATUS_READY


class EventSink:
    def __init__(self):
        self.events = []

    def publish(self, event_type, payload, **kwargs):
        self.events.append((event_type, payload, kwargs))
        return {"success": True}


def test_workflow_engine_emits_task_lifecycle_events_after_persisting(tmp_path):
    sink = EventSink()
    engine = WorkflowEngine(project_dir=str(tmp_path), event_publisher=sink)
    workflow = {
        "workflow_id": "WF-BOT-1",
        "plan_id": "PLAN-BOT-1",
        "title": "bot integration test",
        "status": "ready",
        "paused": False,
        "tasks": [
            {
                "id": "TASK-1", "type": "story", "status": STATUS_READY,
                "progress": 0, "depends_on": [], "started_at": None,
                "finished_at": None, "error": None,
            }
        ],
    }
    engine.save(workflow)

    engine.start_task("WF-BOT-1", "TASK-1")
    engine.complete_task("WF-BOT-1", "TASK-1")

    assert [event[0] for event in sink.events] == ["task.started", "task.completed"]
    assert sink.events[0][1] == {
        "workflow_id": "WF-BOT-1", "plan_id": "PLAN-BOT-1",
        "task_id": "TASK-1", "task_type": "story", "task_status": "running",
    }
    persisted = engine.load("WF-BOT-1")
    assert persisted["tasks"][0]["status"] == "done"
    assert engine.last_event_result == {"success": True}


def test_event_sink_failure_does_not_undo_saved_workflow_state(tmp_path):
    def broken_sink(event_type, payload):
        raise RuntimeError("event store unavailable")

    engine = WorkflowEngine(project_dir=str(tmp_path), event_publisher=broken_sink)
    workflow = {
        "workflow_id": "WF-BOT-2", "plan_id": "PLAN-BOT-2",
        "status": "ready", "paused": False,
        "tasks": [{
            "id": "TASK-2", "type": "story", "status": STATUS_READY,
            "progress": 0, "depends_on": [], "started_at": None,
            "finished_at": None, "error": None,
        }],
    }
    engine.save(workflow)

    engine.start_task("WF-BOT-2", "TASK-2")

    assert engine.load("WF-BOT-2")["tasks"][0]["status"] == "running"
    assert "event store unavailable" in engine.last_event_error


def test_event_sink_result_is_available_for_ui_status(tmp_path):
    class StatusSink:
        def publish(self, event_type, payload, **kwargs):
            return {"success": False, "message": "approval required", "event_type": event_type}

    engine = WorkflowEngine(project_dir=str(tmp_path), event_publisher=StatusSink())
    workflow = {
        "workflow_id": "WF-BOT-3", "plan_id": "PLAN-BOT-3",
        "status": "ready", "paused": False, "tasks": [],
    }
    engine.save(workflow)
    engine._emit("workflow.ready", workflow)

    assert engine.last_event_result["success"] is False
    assert engine.last_event_result["message"] == "approval required"
