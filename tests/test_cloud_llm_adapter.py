"""Optional OpenAI-compatible cloud LLM adapter.

Stdlib-only, like the Ollama director tests: no PySide6, no ComfyUI,
no real gateway is ever called. ``urllib.request.urlopen`` is
monkeypatched, and the adapter is constructed with explicit env
variables so the default-off behaviour is covered too.

Coverage required by the task:
- default disabled: no request is made
- cloud success is parsed (choices[0].message.content)
- 403 / 429 are reported as fallback signals, not raised
- timeout is reported as a fallback signal
- invalid JSON is reported as a fallback signal
- director-plan integration: cloud success records source=cloud;
  cloud 429 silently falls back to Ollama and records cloud_error.
"""

import json
import urllib.error
import urllib.request

import pytest

from core.cloud_llm_adapter import CloudLLMAdapter
from core.local_ollama_director import LocalOllamaDirector


class _FakeResponse:
    def __init__(self, body):
        self._body = body if isinstance(body, bytes) else body.encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _chat_response(content):
    return json.dumps(
        {"choices": [{"message": {"role": "assistant", "content": content}}]},
        ensure_ascii=False,
    )


def _valid_plan_output():
    return {
        "logline": "云端优化后故事",
        "hook": "云端优化后钩子",
        "characters": [{"id": "CHAR-00001", "description": "白衣修仙者，云端优化描述"}],
        "scenes": [{"id": "SCENE-00001", "purpose": "云端优化场景目的"}],
        "shot_items": [
            {"id": "SHOT-0001", "visual_prompt": "云端镜头1", "action": "御剑",
             "dialogue": "", "director_note": "注意1"},
            {"id": "SHOT-0002", "visual_prompt": "云端镜头2", "action": "回眸",
             "dialogue": "", "director_note": "注意2"},
        ],
    }


def base_plan():
    return {
        "plan_id": "PLAN-TEST",
        "title": "测试",
        "idea": "白衣修仙者山间竹林御剑飞行",
        "intent": {"genre": "修仙", "duration_seconds": 10, "aspect_ratio": "9:16"},
        "story": {"logline": "测试故事"},
        "characters": [
            {"id": "CHAR-00001", "name": "主角", "description": "白衣修仙者"},
        ],
        "scenes": [
            {"id": "SCENE-00001", "name": "山间竹林", "purpose": "建立空间"},
        ],
        "shots": [
            {"id": "SHOT-0001", "index": 1, "duration": 5, "scene_id": "SCENE-00001",
             "character_ids": ["CHAR-00001"], "visual_prompt": "白衣修仙者竹林御剑"},
            {"id": "SHOT-0002", "index": 2, "duration": 5, "scene_id": "SCENE-00001",
             "character_ids": ["CHAR-00001"], "visual_prompt": "白衣修仙者落剑回眸"},
        ],
    }


def _set_cloud_env(monkeypatch, enabled="1"):
    monkeypatch.setenv("SCICLOUD_CLOUD_LLM_ENABLED", enabled)
    monkeypatch.setenv("SCICLOUD_CLOUD_LLM_BASE_URL", "http://127.0.0.1:18899/v1")
    monkeypatch.setenv("SCICLOUD_CLOUD_LLM_MODEL", "test-cloud-model")
    monkeypatch.setenv("SCICLOUD_CLOUD_LLM_API_KEY", "test-forward-key")


# ---- Adapter: endpoint resolution ----

def test_endpoint_appends_chat_completions():
    adapter = CloudLLMAdapter(base_url="http://127.0.0.1:18899/v1",
                              model="m", enabled=True)
    assert adapter.endpoint() == "http://127.0.0.1:18899/v1/chat/completions"


def test_endpoint_keeps_full_chat_completions_url():
    adapter = CloudLLMAdapter(base_url="http://127.0.0.1:18899/v1/chat/completions",
                              model="m", enabled=True)
    assert adapter.endpoint() == "http://127.0.0.1:18899/v1/chat/completions"


def test_endpoint_strips_trailing_slash():
    adapter = CloudLLMAdapter(base_url="http://127.0.0.1:18899/v1/",
                              model="m", enabled=True)
    assert adapter.endpoint() == "http://127.0.0.1:18899/v1/chat/completions"


def test_config_summary_never_exposes_api_key():
    adapter = CloudLLMAdapter(base_url="http://127.0.0.1:18899/v1",
                              model="m", api_key="secret-key", enabled=True)
    summary = adapter.config_summary()
    assert "secret-key" not in json.dumps(summary, ensure_ascii=False)
    assert summary["has_api_key"] is True


# ---- Adapter: default off / not configured ----

def test_default_disabled_makes_no_request(monkeypatch):
    monkeypatch.delenv("SCICLOUD_CLOUD_LLM_ENABLED", raising=False)
    monkeypatch.delenv("SCICLOUD_CLOUD_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("SCICLOUD_CLOUD_LLM_MODEL", raising=False)

    def _boom(request, timeout=None):
        raise AssertionError("disabled adapter must not make a request")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    adapter = CloudLLMAdapter()
    assert adapter.enabled is False
    result = adapter.generate_text("hello")
    assert result["ok"] is False
    assert result["error"] == "cloud_disabled"


def test_enabled_but_unconfigured_makes_no_request(monkeypatch):
    monkeypatch.setenv("SCICLOUD_CLOUD_LLM_ENABLED", "1")
    monkeypatch.delenv("SCICLOUD_CLOUD_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("SCICLOUD_CLOUD_LLM_MODEL", raising=False)

    def _boom(request, timeout=None):
        raise AssertionError("unconfigured adapter must not make a request")

    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    adapter = CloudLLMAdapter()
    assert adapter.is_configured is False
    result = adapter.generate_text("hello")
    assert result["error"] == "cloud_not_configured"


# ---- Adapter: success and failure signals ----

def test_cloud_success_parses_content(monkeypatch):
    _set_cloud_env(monkeypatch)
    monkeypatch.setattr(
        urllib.request, "urlopen",
        lambda request, timeout=None: _FakeResponse(_chat_response("云端回答")))
    adapter = CloudLLMAdapter()
    result = adapter.generate_text("hello")
    assert result["ok"] is True
    assert result["text"] == "云端回答"


def test_cloud_http_403_is_fallback_signal(monkeypatch):
    _set_cloud_env(monkeypatch)

    def _raise(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", _raise)
    result = CloudLLMAdapter().generate_text("hello")
    assert result["ok"] is False
    assert result["error"] == "cloud_http_403"


def test_cloud_http_429_is_fallback_signal(monkeypatch):
    _set_cloud_env(monkeypatch)

    def _raise(request, timeout=None):
        raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", _raise)
    result = CloudLLMAdapter().generate_text("hello")
    assert result["ok"] is False
    assert result["error"] == "cloud_http_429"


def test_cloud_timeout_is_fallback_signal(monkeypatch):
    _set_cloud_env(monkeypatch)

    def _raise(request, timeout=None):
        raise urllib.error.URLError(TimeoutError("timed out"))

    monkeypatch.setattr(urllib.request, "urlopen", _raise)
    result = CloudLLMAdapter().generate_text("hello")
    assert result["ok"] is False
    assert result["error"] == "cloud_timeout"


def test_cloud_invalid_json_is_fallback_signal(monkeypatch):
    _set_cloud_env(monkeypatch)
    monkeypatch.setattr(
        urllib.request, "urlopen",
        lambda request, timeout=None: _FakeResponse("这不是 JSON"))
    result = CloudLLMAdapter().generate_text("hello")
    assert result["ok"] is False
    assert result["error"] == "cloud_invalid_json"


def test_cloud_empty_content_is_fallback_signal(monkeypatch):
    _set_cloud_env(monkeypatch)
    monkeypatch.setattr(
        urllib.request, "urlopen",
        lambda request, timeout=None: _FakeResponse(_chat_response("   ")))
    result = CloudLLMAdapter().generate_text("hello")
    assert result["ok"] is False
    assert result["error"] == "cloud_empty_content"


# ---- Director integration: cloud first, Ollama fallback ----

def test_director_cloud_success_records_source_cloud(monkeypatch):
    _set_cloud_env(monkeypatch)
    monkeypatch.setattr(
        urllib.request, "urlopen",
        lambda request, timeout=None: _FakeResponse(
            _chat_response(json.dumps(_valid_plan_output(), ensure_ascii=False))))
    plan = base_plan()
    result = LocalOllamaDirector().enrich_plan(plan)
    assert result["mode"] == "cloud_llm"
    assert result["source"] == "cloud"
    assert result["diagnosis"] == "ok"
    assert plan["shots"][0]["visual_prompt"] == "云端镜头1"
    assert plan["shots"][1]["visual_prompt"] == "云端镜头2"


def test_director_cloud_429_falls_back_to_ollama_silently(monkeypatch):
    _set_cloud_env(monkeypatch)

    def _route(request, timeout=None):
        url = request.full_url if hasattr(request, "full_url") else str(request)
        if "/chat/completions" in url:
            raise urllib.error.HTTPError(url, 429, "Too Many Requests", {}, None)
        if "/api/tags" in url:
            return _FakeResponse(json.dumps({"models": [{"name": "qwen2.5:3b"}]}))
        if "/api/generate" in url:
            return _FakeResponse(json.dumps(
                {"response": json.dumps(_valid_plan_output(), ensure_ascii=False)}))
        raise AssertionError("unexpected url: %s" % url)

    monkeypatch.setattr(urllib.request, "urlopen", _route)
    plan = base_plan()
    result = LocalOllamaDirector().enrich_plan(plan)
    # Plan creation did not fail: Ollama covered the cloud outage.
    assert result["mode"] == "local_ollama"
    assert result["source"] == "ollama"
    assert result["cloud_attempted"] is True
    assert result["cloud_error"] == "cloud_http_429"
    assert plan["shots"][0]["visual_prompt"] == "云端镜头1"


def test_director_disabled_cloud_behaves_like_before(monkeypatch):
    monkeypatch.setenv("SCICLOUD_CLOUD_LLM_ENABLED", "0")
    monkeypatch.delenv("SCICLOUD_CLOUD_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("SCICLOUD_CLOUD_LLM_MODEL", raising=False)

    def _route(request, timeout=None):
        url = request.full_url if hasattr(request, "full_url") else str(request)
        if "/api/tags" in url:
            return _FakeResponse(json.dumps({"models": []}))
        raise AssertionError("unexpected url: %s" % url)

    monkeypatch.setattr(urllib.request, "urlopen", _route)
    result = LocalOllamaDirector().enrich_plan(base_plan())
    assert result["mode"] == "deterministic_fallback"
    assert result["source"] == "rule"
    assert result["cloud_attempted"] is False
