"""Production Bot: bridge workflow-ready events to the existing AutoDirector.

The Bot is approval-gated by default. Configuration is idempotent for a given
runtime/engine pair so UI reloads and tests cannot register duplicate handlers.
"""
from __future__ import annotations

from typing import Any

from core.auto_director import auto_director
from core.bot_runtime import bot_runtime
from core.workflow_engine import workflow_engine

HANDLER_ID = "scicloud.production_bot.workflow_ready.v1"
_CONFIGURED: list[tuple[Any, Any, "ProductionBot"]] = []


class ProductionBot:
    """Handle workflow-ready events using the existing AutoDirector."""

    def __init__(self, director: Any = auto_director, *, auto_execute: bool = False):
        self.director = director
        self.auto_execute = bool(auto_execute)

    def handle_workflow_ready(self, event: dict[str, Any]) -> dict[str, Any]:
        payload = event.get("payload") or {}
        workflow_id = payload.get("workflow_id")
        if not isinstance(workflow_id, str) or not workflow_id.strip():
            raise ValueError("workflow.ready 事件缺少有效 workflow_id")
        if not self.auto_execute:
            return {
                "success": True,
                "queued": False,
                "requires_approval": True,
                "workflow_id": workflow_id,
                "message": "工作流已就绪；自动执行未启用，等待用户确认",
            }
        result = self.director.run(workflow_id)
        if not isinstance(result, dict):
            raise TypeError("AutoDirector.run 必须返回字典结果")
        return {
            "success": bool(result.get("success")),
            "queued": False,
            "requires_approval": False,
            "workflow_id": workflow_id,
            "execution": result,
        }

    def approve_and_run(self, workflow_id: str, *, max_steps: int = 50) -> dict[str, Any]:
        """Explicit user-triggered execution; never called by startup registration."""
        if not isinstance(workflow_id, str) or not workflow_id.strip():
            raise ValueError("批准执行需要有效 workflow_id")
        result = self.director.run(workflow_id, max_steps=max_steps)
        if not isinstance(result, dict):
            raise TypeError("AutoDirector.run 必须返回字典结果")
        return {
            "success": bool(result.get("success")),
            "requires_approval": False,
            "workflow_id": workflow_id,
            "execution": result,
        }


def configure_production_bot(
    runtime: Any = bot_runtime,
    engine: Any = workflow_engine,
    director: Any = auto_director,
    *,
    auto_execute: bool = False,
) -> ProductionBot:
    """Wire lifecycle publishing once per runtime/engine pair.

    Reconfiguration updates the existing Bot's policy and director without
    subscribing a second handler. Automatic execution remains opt-in.
    """
    for configured_runtime, configured_engine, configured_bot in _CONFIGURED:
        if configured_runtime is runtime and configured_engine is engine:
            configured_bot.director = director
            configured_bot.auto_execute = bool(auto_execute)
            engine.event_publisher = runtime
            return configured_bot

    bot = ProductionBot(director, auto_execute=auto_execute)
    engine.event_publisher = runtime
    runtime.subscribe("workflow.ready", bot.handle_workflow_ready, handler_id=HANDLER_ID)
    _CONFIGURED.append((runtime, engine, bot))
    return bot
