"""Production Bot: bridge workflow-ready events to the existing AutoDirector.

Importing this module has no side effects. Call configure_production_bot explicitly
from application startup after the user has chosen whether automatic execution is
allowed. The Bot delegates execution; it does not implement a second scheduler.
"""
from __future__ import annotations

from typing import Any

from core.auto_director import auto_director
from core.bot_runtime import bot_runtime
from core.workflow_engine import workflow_engine


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
        return {
            "success": bool(result.get("success")),
            "queued": False,
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
    """Wire lifecycle publishing and the Production Bot; call once at app startup.

    Automatic execution is disabled unless the caller explicitly opts in. This
    avoids unexpectedly starting a long render merely because a project is opened.
    """
    bot = ProductionBot(director, auto_execute=auto_execute)
    engine.event_publisher = runtime
    runtime.subscribe(
        "workflow.ready",
        bot.handle_workflow_ready,
        handler_id="scicloud.production_bot.workflow_ready.v1",
    )
    return bot
