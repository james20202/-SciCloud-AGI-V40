"""Optional OpenAI-compatible cloud LLM adapter (text only).

This module is deliberately small and stdlib-only (urllib/json): it adds
no new dependency and it never touches rendering, ComfyUI, TTS, or VLM.

Design, following the dsh-our-free-model local-forward idea without
copying that JS plugin into SciCloud:

- The adapter speaks the OpenAI-compatible ``/v1/chat/completions``
  surface, non-streaming. It is meant to point at a *local* forward
  listener (for example the one dsh-our-free-model exposes, typically
  ``http://127.0.0.1:18899/v1``) or, equivalently, at any other
  OpenAI-compatible endpoint the user configures.
- It is OFF by default. It only runs when the user explicitly opts in
  through environment variables, and it is only used on the text
  generation path (director plan / script / prompts). Image and video
  generation still go through the local ComfyUI path.
- Every failure is reported as a stable error code and never raises
  into the caller: the director path must silently fall back to the
  existing local Ollama path, and then to the deterministic rule
  fallback, so a cloud outage can never make plan creation fail.

Configuration (environment variables, read at construction time):

- ``SCICLOUD_CLOUD_LLM_ENABLED``: ``1``/``true``/``yes``/``on`` to
  enable; anything else (including unset) means disabled.
- ``SCICLOUD_CLOUD_LLM_BASE_URL``: for example
  ``http://127.0.0.1:18899/v1``. ``/chat/completions`` is appended
  automatically when it is not already present.
- ``SCICLOUD_CLOUD_LLM_MODEL``: model id to request, for example a
  free-lane text model served by the forward listener.
- ``SCICLOUD_CLOUD_LLM_API_KEY``: key for the forward listener, if it
  requires one. It is sent only as a Bearer header and is never
  included in any returned detail string, log, or plan record.

Free-lane caveats (see the PR description): prompts sent through this
adapter leave the machine and go to the upstream gateway that serves
the model; a free pool may log prompts, may be region-gated, may
answer 403/429 when its allowance is spent, and its model roster can
change or be withdrawn at any time. Do not send sensitive content
through it, and do not treat it as the primary path: local Ollama
remains the default.
"""

import json
import os
import urllib.error
import urllib.request

_ENABLED_VALUES = {"1", "true", "yes", "on"}


def _is_enabled(value):
    return str(value or "").strip().lower() in _ENABLED_VALUES


class CloudLLMAdapter:
    """Minimal OpenAI-compatible chat-completions client."""

    def __init__(self, base_url=None, model=None, api_key=None,
                 enabled=None, timeout=60):
        if enabled is None:
            enabled = _is_enabled(os.environ.get("SCICLOUD_CLOUD_LLM_ENABLED", ""))
        self.enabled = bool(enabled)
        self.base_url = (base_url if base_url is not None
                         else os.environ.get("SCICLOUD_CLOUD_LLM_BASE_URL", "")).strip()
        self.model = (model if model is not None
                      else os.environ.get("SCICLOUD_CLOUD_LLM_MODEL", "")).strip()
        # Never expose this value: it is only ever used as a header.
        self._api_key = (api_key if api_key is not None
                         else os.environ.get("SCICLOUD_CLOUD_LLM_API_KEY", "")).strip()
        self.timeout = timeout

    @property
    def is_configured(self):
        """True when the adapter is enabled AND has somewhere to call."""
        return self.enabled and bool(self.base_url) and bool(self.model)

    def endpoint(self):
        """Resolve the chat-completions URL from the configured base URL."""
        base = self.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return base + "/chat/completions"

    def config_summary(self):
        """Safe summary for UI display: never includes the API key."""
        return {
            "enabled": self.enabled,
            "configured": self.is_configured,
            "base_url": self.base_url,
            "endpoint": self.endpoint() if self.base_url else "",
            "model": self.model,
            "has_api_key": bool(self._api_key),
        }

    def generate_text(self, prompt, system_prompt=None):
        """One non-streaming chat-completions call.

        Returns a dict with ``ok`` and, on success, ``text``. On
        failure it returns ``ok=False`` plus a stable ``error`` code
        and a short ``detail`` that never contains the API key:

        - ``cloud_disabled``: adapter not enabled.
        - ``cloud_not_configured``: enabled but base URL or model missing.
        - ``cloud_http_<code>``: upstream answered with an HTTP error
          (403/429 are the common free-lane quota/region answers).
        - ``cloud_timeout``: request timed out.
        - ``cloud_network_error``: connection refused / DNS / other
          transport failure.
        - ``cloud_invalid_json``: response body was not valid JSON.
        - ``cloud_invalid_response``: JSON shape was not a usable
          chat-completions response.
        - ``cloud_empty_content``: model returned no usable text.
        - ``cloud_error``: anything else.
        """
        if not self.enabled:
            return {"ok": False, "error": "cloud_disabled",
                    "detail": "云端 LLM 未开启（SCICLOUD_CLOUD_LLM_ENABLED 未设为开启）"}
        if not self.base_url or not self.model:
            return {"ok": False, "error": "cloud_not_configured",
                    "detail": "云端 LLM 已开启但缺少 SCICLOUD_CLOUD_LLM_BASE_URL 或 SCICLOUD_CLOUD_LLM_MODEL"}
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "temperature": 0.3,
        }
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = "Bearer " + self._api_key
        request = urllib.request.Request(
            self.endpoint(),
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return {"ok": False, "error": "cloud_http_%s" % exc.code,
                    "detail": "云端模型返回 HTTP %s" % exc.code}
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, TimeoutError) or "timed out" in str(reason).lower():
                return {"ok": False, "error": "cloud_timeout",
                        "detail": "云端模型请求超时"}
            return {"ok": False, "error": "cloud_network_error",
                    "detail": "无法连接云端模型地址：%s" % reason}
        except TimeoutError:
            return {"ok": False, "error": "cloud_timeout",
                    "detail": "云端模型请求超时"}
        except Exception as exc:
            return {"ok": False, "error": "cloud_error",
                    "detail": "云端模型请求出错：%s" % exc}
        try:
            data = json.loads(raw)
        except Exception:
            return {"ok": False, "error": "cloud_invalid_json",
                    "detail": "云端模型返回不是合法 JSON"}
        if not isinstance(data, dict) or not isinstance(data.get("choices"), list) \
                or not data["choices"]:
            return {"ok": False, "error": "cloud_invalid_response",
                    "detail": "云端模型返回不是可用的 chat completions 结构"}
        first = data["choices"][0]
        message = first.get("message") if isinstance(first, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str) or not content.strip():
            return {"ok": False, "error": "cloud_empty_content",
                    "detail": "云端模型没有返回可用文本"}
        return {"ok": True, "text": content.strip(), "model": self.model}


# Module-level instance, mirroring local_ollama_director. The director
# path constructs a fresh adapter per plan instead, so an environment
# change does not require reading stale import-time state.
cloud_llm_adapter = CloudLLMAdapter()
