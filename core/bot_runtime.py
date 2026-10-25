"""Small local event runtime for event-driven production bots.

The runtime is deliberately model-free and synchronous. JSONL records provide an
audit trail and persistent per-handler completion checkpoints so retries do not
repeat handlers that already completed successfully.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

Handler = Callable[[dict[str, Any]], Any]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _fingerprint(event_type: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        {"event_type": event_type, "payload": payload},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _handler_key(handler: Handler, handler_id: str | None) -> str:
    if handler_id is not None:
        if not isinstance(handler_id, str) or not handler_id.strip():
            raise ValueError("handler_id 必须是非空字符串")
        return handler_id.strip()
    return f"{getattr(handler, '__module__', '')}.{getattr(handler, '__qualname__', type(handler).__qualname__)}"


class BotRuntime:
    """Dispatch named events with persistent event and handler idempotency."""

    def __init__(self, event_log_path: str | None = None):
        self.event_log_path = event_log_path
        self._handlers: dict[str, list[tuple[str, Handler]]] = {}
        self._completed_ids: set[str] = set()
        self._completed_handlers: dict[str, set[str]] = {}
        self._event_fingerprints: dict[str, str] = {}
        self._lock = threading.RLock()
        if event_log_path:
            os.makedirs(os.path.dirname(os.path.abspath(event_log_path)), exist_ok=True)
            self._load_log_state()

    def subscribe(self, event_type: str, handler: Handler, *, handler_id: str | None = None) -> None:
        if not isinstance(event_type, str) or not event_type.strip():
            raise ValueError("event_type 必须是非空字符串")
        if not callable(handler):
            raise TypeError("handler 必须可调用")
        key = _handler_key(handler, handler_id)
        with self._lock:
            handlers = self._handlers.setdefault(event_type, [])
            if handler_id is None:
                base_key = key
                suffix = 2
                while any(existing_key == key and existing_handler is not handler for existing_key, existing_handler in handlers):
                    key = f"{base_key}#{suffix}"
                    suffix += 1
            elif any(existing_key == key and existing_handler is not handler for existing_key, existing_handler in handlers):
                raise ValueError(f"同一事件的 handler_id 重复：{key}")
            if not any(existing_key == key for existing_key, _ in handlers):
                handlers.append((key, handler))

    def _append(self, record: dict[str, Any]) -> None:
        if not self.event_log_path:
            return
        with open(self.event_log_path, "a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()

    def _load_log_state(self) -> None:
        if not self.event_log_path or not os.path.isfile(self.event_log_path):
            return
        try:
            with open(self.event_log_path, encoding="utf-8") as stream:
                for line in stream:
                    try:
                        record = json.loads(line)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    event_id = record.get("event_id")
                    if not event_id:
                        continue
                    event_id = str(event_id)
                    kind = record.get("record_type")
                    if kind == "event_received" and record.get("fingerprint"):
                        self._event_fingerprints[event_id] = str(record["fingerprint"])
                    elif kind == "handler_completed" and record.get("handler_id"):
                        self._completed_handlers.setdefault(event_id, set()).add(str(record["handler_id"]))
                    elif kind == "event_completed":
                        self._completed_ids.add(event_id)
        except OSError:
            # A missing/unreadable log must not prevent the desktop UI from starting.
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
        fingerprint = _fingerprint(event_type, payload)
        if not isinstance(source, str) or not source.strip():
            raise ValueError("source 必须是非空字符串")
        identifier = event_id or str(uuid.uuid4())
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("event_id 必须是非空字符串")

        event = {
            "event_id": identifier, "event_type": event_type, "payload": payload,
            "source": source, "created_at": _now(),
        }
        with self._lock:
            previous_fingerprint = self._event_fingerprints.get(identifier)
            if previous_fingerprint and previous_fingerprint != fingerprint:
                return {
                    "success": False, "duplicate": False, "event_id": identifier,
                    "handled": 0, "results": [], "errors": [],
                    "message": "event_id 已用于不同的事件内容，拒绝复用",
                }
            if identifier in self._completed_ids:
                return {"success": True, "duplicate": True, "event_id": identifier, "handled": 0, "results": []}

            handlers = list(self._handlers.get(event_type, ()))
            if not handlers:
                self._append({"record_type": "event_unhandled", **event})
                return {
                    "success": False, "duplicate": False, "event_id": identifier,
                    "handled": 0, "results": [], "message": f"没有 Bot 订阅事件：{event_type}",
                }

            if not previous_fingerprint:
                self._append({"record_type": "event_received", **event, "fingerprint": fingerprint})
                self._event_fingerprints[identifier] = fingerprint

            completed = self._completed_handlers.setdefault(identifier, set())
            results, errors, handled = [], [], 0
            for index, (handler_id, handler) in enumerate(handlers):
                if handler_id in completed:
                    results.append({"handler_id": handler_id, "success": True, "skipped": True})
                    continue
                handled += 1
                self._append({
                    "record_type": "handler_started", "event_id": identifier,
                    "event_type": event_type, "handler_id": handler_id, "handler_index": index, "at": _now(),
                })
                try:
                    result = handler(event)
                    # A non-JSON-safe result is treated as failure, not checkpointed.
                    json.dumps(result, ensure_ascii=False, allow_nan=False)
                    self._append({
                        "record_type": "handler_completed", "event_id": identifier,
                        "event_type": event_type, "handler_id": handler_id, "handler_index": index, "at": _now(),
                    })
                    completed.add(handler_id)
                    results.append({"handler_id": handler_id, "success": True, "result": result})
                except Exception as exc:
                    errors.append({"handler_id": handler_id, "handler_index": index, "error": str(exc)})
                    self._append({
                        "record_type": "handler_finished", "event_id": identifier,
                        "event_type": event_type, "handler_id": handler_id, "handler_index": index,
                        "success": False, "error": str(exc), "at": _now(),
                    })

            success = not errors and all(key in completed for key, _ in handlers)
            if success:
                self._append({"record_type": "event_completed", "event_id": identifier, "event_type": event_type, "at": _now()})
                self._completed_ids.add(identifier)
            return {
                "success": success, "duplicate": False, "event_id": identifier,
                "handled": handled, "results": results, "errors": errors,
            }


bot_runtime = BotRuntime()
