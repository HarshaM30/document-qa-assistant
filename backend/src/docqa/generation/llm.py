"""LiteLLM model specs built from settings (provider + model), for answering and judging."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from docqa.config import Settings
from docqa.generation.fake_provider import FAKE_PROVIDER, register_fake_provider


@dataclass(frozen=True)
class LLMSpec:
    provider: str
    model: str
    temperature: float
    max_tokens: int
    timeout_seconds: float
    reasoning_effort: str | None
    api_key: str | None

    @property
    def litellm_model(self) -> str:
        """LiteLLM routes on the prefix, e.g. "groq/openai/gpt-oss-120b"."""
        return f"{self.provider}/{self.model}"

    @property
    def is_reasoning_model(self) -> bool:
        return self.provider != FAKE_PROVIDER and "gpt-oss" in self.model

    def completion_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.litellm_model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout_seconds,
            "num_retries": 0,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        # Hidden reasoning tokens count against the per-minute token limit; keep them few.
        if self.reasoning_effort and self.is_reasoning_model:
            kwargs["reasoning_effort"] = self.reasoning_effort
        return kwargs


def _api_key(settings: Settings, provider: str) -> str | None:
    if provider == "groq":
        return settings.groq_api_key.get_secret_value() or None
    return None


def _spec(settings: Settings, provider: str, model: str) -> LLMSpec:
    if provider == FAKE_PROVIDER:
        register_fake_provider()
    return LLMSpec(
        provider=provider,
        model=model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout_seconds=settings.llm_timeout_seconds,
        reasoning_effort=settings.llm_reasoning_effort or None,
        api_key=_api_key(settings, provider),
    )


def answer_llm(settings: Settings) -> LLMSpec:
    return _spec(settings, settings.llm_provider, settings.llm_model)


def judge_llm(settings: Settings) -> LLMSpec:
    return _spec(settings, settings.judge_provider, settings.judge_model)


@dataclass
class ProbeResult:
    reply: str = ""
    latency_ms: int = 0
    rate_limits: dict[str, str] = field(default_factory=dict)
    error: str | None = None


def _rate_limit_headers(response: Any) -> dict[str, str]:
    headers = (getattr(response, "_hidden_params", None) or {}).get("additional_headers") or {}
    out = {}
    for key, value in headers.items():
        name = str(key).lower().removeprefix("llm_provider-")
        if name.startswith("x-ratelimit-"):
            out[name] = str(value)
    return out


def probe(spec: LLMSpec) -> ProbeResult:
    """One tiny, non-streamed completion: confirms the model exists for this key."""
    import litellm
    from litellm.exceptions import APIError, NotFoundError

    kwargs = spec.completion_kwargs() | {"max_tokens": 256}
    started = time.monotonic()
    try:
        response = litellm.completion(
            messages=[{"role": "user", "content": "Reply with the single word: ok"}], **kwargs
        )
    except NotFoundError as exc:
        return ProbeResult(error=f"model_not_found ({exc.message})")
    except APIError as exc:
        return ProbeResult(error=f"{type(exc).__name__}: {exc.message}")
    except Exception as exc:
        return ProbeResult(error=f"{type(exc).__name__}: {exc}")
    return ProbeResult(
        reply=(response.choices[0].message.content or "").strip(),
        latency_ms=int((time.monotonic() - started) * 1000),
        rate_limits=_rate_limit_headers(response),
    )
