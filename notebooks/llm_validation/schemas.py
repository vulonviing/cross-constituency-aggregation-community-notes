from __future__ import annotations

import json
from dataclasses import dataclass

from prompts import STAGE1_LABELS, STAGE15_LABELS


class SchemaError(ValueError):
    pass


@dataclass(frozen=True)
class Stage1Response:
    label: str
    reason: str


@dataclass(frozen=True)
class Stage2Response:
    rescue_worthiness: int
    reason: str


def _load_object(raw: str, expected_keys: set[str]) -> dict:
    candidate = raw.strip()
    if candidate.startswith("```"):
        candidate = candidate[3:]
        if candidate.startswith("json"):
            candidate = candidate[4:]
        if candidate.endswith("```"):
            candidate = candidate[:-3]
        candidate = candidate.strip()
    # OpenCode's Fireworks GLM route can prepend a literal {" before an
    # otherwise valid JSON object while JSON mode is enabled.
    if candidate.startswith('{"{'):
        candidate = candidate[2:]
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise SchemaError(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise SchemaError("response must be a JSON object")
    if set(value) != expected_keys:
        raise SchemaError(
            f"response keys must be exactly {sorted(expected_keys)}; got {sorted(value)}"
        )
    return value


def _validate_reason(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaError("reason must be a non-empty string")
    reason = value.strip()
    if len(reason.split()) > 40:
        raise SchemaError("reason exceeds 40 words")
    return reason


def parse_stage1(raw: str) -> Stage1Response:
    value = _load_object(raw, {"label", "reason"})
    label = value["label"]
    if label not in STAGE1_LABELS:
        raise SchemaError(f"unknown Stage 1 label: {label!r}")
    return Stage1Response(label=label, reason=_validate_reason(value["reason"]))


def parse_stage15(raw: str) -> Stage1Response:
    value = _load_object(raw, {"label", "reason"})
    label = value["label"]
    if label not in STAGE15_LABELS:
        raise SchemaError(f"unknown Stage 1.5 label: {label!r}")
    return Stage1Response(label=label, reason=_validate_reason(value["reason"]))


def parse_stage2(raw: str) -> Stage2Response:
    value = _load_object(raw, {"rescue_worthiness", "reason"})
    score = value["rescue_worthiness"]
    if isinstance(score, bool) or not isinstance(score, int):
        raise SchemaError("rescue_worthiness must be an integer")
    if not 0 <= score <= 100:
        raise SchemaError("rescue_worthiness must be between 0 and 100")
    return Stage2Response(
        rescue_worthiness=score,
        reason=_validate_reason(value["reason"]),
    )
