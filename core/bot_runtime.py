"""Small local event runtime for event-driven production bots.

This module deliberately contains no model calls and no background threads. Domain
bots subscribe to typed events; existing workflow/execution engines remain responsible
for doing production work. JSONL records provide an audit trail and completed-event
deduplication across application restarts.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable


Handler = Callable[[dict[str, Any]], Any]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class BotRuntime:
    """Dispatch named events to registered handlers with persistent idempotency."""

    def __init__(self, event_log_path: str | None = None):
        self.event_log_path = event_log_path
        self._handlers: dict[str, list[Handler]] = {}
        self._completed_ids: set[str] = set()
        self._lock = threading.RLock()
        if event_log_path:
            parent = os.path.dirname(os.path.abspath(event_log_path))
            os.makedirs(parent, exist_ok=True)
            self._load_completed_ids()

    def subscribe(self, event_type: str, handler: Handler) -> None:
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("event_type 必须是非空字符串")
        if not callable(handler):
            raise TypeError("handler 必须可调用")
        with self._lock:
            handlers = self._handlers.setdefault(event_type, [])
            if handler not in handlers:
                handlers.append(handler)

    def _append(self, record: dict[str, Any]) -> None:
        if not self.event_log_path:
            return
        with open(self.event_log_path, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()

    def _load_completed_ids(self) -> None:
        if not self.event_log_path or not os.path.isfile(self.event_log_path):
            return
        try:
            with open(self.event_log_path, encoding="utf-8") as stream:
                for line in stream:
                    try:
                        record = json.loads(line)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if record.get("record_type") == "event_completed" and record.get("event_id"):
                        self._completed_ids.add(str(record["event_id"]))
        except OSError:
            # A missing/unreadable log must not prevent the UI from starting.
            return

    def publish(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        event_id: str | None = None,
        source: str = "local",
    ) -> dict[str, Any]:
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("event_type 必须是非空字符串")
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            raise TypeError("payload 必须是字典")
        # Validate serializability before recording or invoking any side effect.
        json.dumps(payload, ensure_ascii=False, allow_nan=False)
        if not isinstance(source, str) or not source.strip():
            raise ValueError("source 必须是非空字符串")

        identifier = event_id or str(uuid.uuid4())
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("event_id 必须是非空字符串")
        event = {
            "event_id": identifier,
            "event_type": event_type,
            "payload": payload,
            "source": source,
            "created_at": _now(),
        }

        with self._lock:
            if identifier in self._completed_ids:
                return {
                    "success": True,
                    "duplicate": True,
                    "event_id": identifier,
                    "handled": 0,
                    "results": [],
                }
            handlers = list(self._handlers.get(event_type, ()))
            if not handlers:
                self._append({"record_type": "event_unhandled", **event})
                return {
                    "success": False,
                    "duplicate": False,
                    "event_id": identifier,
                    "handled": 0,
                    "results": [],
                    "message": f"没有 Bot 订阅事件：{event_type}",
                }

            self._append({"record_type": "event_received", **event})
            results = []
            errors = []
            for index, handler in enumerate(handlers):
                self._append({
                    "record_type": "handler_started",
                    "event_id": identifier,
                    "event_type": event_type,
                    "handler_index": index,
                    "at": _now(),
                })
                try:
                    result = handler(event)
                    # Keep the log JSON-safe even if a handler returns an object.
                    json.dumps(result, ensure_ascii=False, allow_nan=False)
                    results.append({"handler_index": index, "success": True, "result": result})
                    self._append({
                        "record_type": "handler_finished",
                        "event_id": identifier,
                        "event_type": event_type,
                        "handler_index": index,
                        "success": True,
                        "at": _now(),
                    })
                except Exception as exc:
                    errors.append({"handler_index": index, "error": str(exc)})
                    self._append({
                        "record_type": "handler_finished",
                        "event_id": identifier,
                        "event_type": event_type,
                        "handler_index": index,
                        "success": False,
                        "error": str(exc),
                        "at": _now(),
                    })

            success = not errors
            if success:
                self._append({
                    "record_type": "event_completed",
                    "event_id": identifier,
                    "event_type": event_type,
                    "at": _now(),
                })
                self._completed_ids.add(identifier)
            return {
                "success": success,
                "duplicate": False,
                "event_id": identifier,
                "handled": len(handlers),
                "results": results,
                "errors": errors,
            }


bot_runtime = BotRuntime()
