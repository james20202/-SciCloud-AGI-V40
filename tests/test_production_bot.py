from core.production_bot import ProductionBot, configure_production_bot


class FakeRuntime:
    def __init__(self):
        self.subscriptions = {}

    def subscribe(self, event_type, handler, *, handler_id=None):
        self.subscriptions[event_type] = (handler, handler_id)


class FakeEngine:
    event_publisher = None


class FakeDirector:
    def __init__(self, result=None):
        self.calls = []
        self.result = result or {"success": True, "message": "completed", "steps": 4}

    def run(self, workflow_id):
        self.calls.append(workflow_id)
        return self.result


def test_production_bot_requires_explicit_auto_execute_opt_in():
    director = FakeDirector()
    bot = ProductionBot(director)

    result = bot.handle_workflow_ready({
        "event_id": "evt-1",
        "payload": {"workflow_id": "WF-1"},
    })

    assert result["success"] is True
    assert result["requires_approval"] is True
    assert director.calls == []


def test_production_bot_delegates_to_existing_auto_director_when_enabled():
    director = FakeDirector()
    bot = ProductionBot(director, auto_execute=True)

    result = bot.handle_workflow_ready({
        "event_id": "evt-2",
        "payload": {"workflow_id": "WF-2"},
    })

    assert result["success"] is True
    assert result["requires_approval"] is False
    assert result["execution"]["steps"] == 4
    assert director.calls == ["WF-2"]


def test_production_bot_rejects_event_without_workflow_id():
    bot = ProductionBot(FakeDirector())
    try:
        bot.handle_workflow_ready({"payload": {}})
    except ValueError as exc:
        assert "workflow_id" in str(exc)
    else:
        raise AssertionError("expected invalid workflow event to be rejected")


def test_configure_wires_runtime_and_subscriber_without_starting_execution():
    runtime, engine, director = FakeRuntime(), FakeEngine(), FakeDirector()

    bot = configure_production_bot(runtime, engine, director)

    assert engine.event_publisher is runtime
    handler, handler_id = runtime.subscriptions["workflow.ready"]
    assert handler == bot.handle_workflow_ready
    assert handler_id == "scicloud.production_bot.workflow_ready.v1"
    assert director.calls == []
