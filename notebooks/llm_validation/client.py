from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from config import (
    BASE_URL,
    MAX_COMPLETION_TOKENS,
    MODEL,
    REQUEST_TIMEOUT_SECONDS,
    TEMPERATURE,
)


@dataclass(frozen=True)
class GatewayResponse:
    raw_response: str
    reasoning: str | None
    returned_model: str
    finish_reason: str | None
    usage: dict[str, int]


def _integer(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _usage_dict(usage: Any) -> dict[str, int]:
    if usage is None:
        return {
            "prompt_tokens": 0,
            "cached_tokens": 0,
            "completion_tokens": 0,
            "reasoning_tokens": 0,
        }
    data = usage.model_dump() if hasattr(usage, "model_dump") else dict(usage)
    prompt_details = data.get("prompt_tokens_details") or {}
    completion_details = data.get("completion_tokens_details") or {}
    return {
        "prompt_tokens": _integer(data.get("prompt_tokens")),
        "cached_tokens": _integer(prompt_details.get("cached_tokens")),
        "completion_tokens": _integer(data.get("completion_tokens")),
        "reasoning_tokens": _integer(completion_details.get("reasoning_tokens")),
    }


def _reasoning_text(message: Any) -> str | None:
    reasoning = getattr(message, "reasoning", None)
    if reasoning is None:
        reasoning = getattr(message, "reasoning_content", None)
    if reasoning is None and getattr(message, "model_extra", None):
        reasoning = message.model_extra.get("reasoning_content")
    return reasoning if isinstance(reasoning, str) and reasoning.strip() else None


class EmptyContentError(RuntimeError):
    pass


class TruncatedResponseError(RuntimeError):
    pass


class LocalVLLMClient:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key="local-vllm",
            base_url=BASE_URL,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

    async def close(self) -> None:
        await self._client.close()

    async def complete(self, prompt: str, *, seed: int) -> GatewayResponse:
        response = await self._client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=TEMPERATURE,
            max_completion_tokens=MAX_COMPLETION_TOKENS,
            seed=seed,
            extra_body={"chat_template_kwargs": {"enable_thinking": True}},
        )
        if not response.choices:
            raise RuntimeError("vLLM returned no choices")
        choice = response.choices[0]
        message = choice.message
        content = message.content
        reasoning = _reasoning_text(message)
        if choice.finish_reason == "length":
            raise TruncatedResponseError(
                f"vLLM reached max_completion_tokens={MAX_COMPLETION_TOKENS}"
            )
        if not isinstance(content, str) or not content.strip():
            raise EmptyContentError("vLLM returned no final text content")
        return GatewayResponse(
            raw_response=content,
            reasoning=reasoning,
            returned_model=str(response.model or ""),
            finish_reason=choice.finish_reason,
            usage=_usage_dict(response.usage),
        )
