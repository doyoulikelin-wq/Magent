"""Payload validation gateway for AgentActions.

Validates ``payload`` against the JSON schema for the given
``action_type`` + ``payload_version``.  On failure the action is
marked ``invalid`` / ``degraded`` and a safe fallback payload is
substituted so the user never sees a broken card.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

import jsonschema  # type: ignore[import-untyped]
from jsonschema import ValidationError

from app.services.payload_schemas import get_schema

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Safe fallback payloads (one per action_type)
# ---------------------------------------------------------------------------

_SAFE_FALLBACK: dict[str, dict[str, Any]] = {
    "pre_meal_sim": {
        "title": "吃前预演（暂不可用）",
        "message": "系统正在优化预测模型，请稍后重试。",
    },
    "rescue": {
        "title": "吃后建议（暂不可用）",
        "message": "当前无法生成个性化补救方案，建议保持活动并关注血糖趋势。",
    },
    "daily_plan": {
        "title": "今日代谢天气（暂不可用）",
        "message": "今日计划生成中遇到问题，请稍后刷新。",
    },
    "weekly_goal": {
        "title": "周目标（暂不可用）",
        "message": "本周目标生成暂不可用，请稍后查看。",
    },
}


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Outcome of payload validation."""

    valid: bool
    payload: dict[str, Any]  # original or safe fallback
    status: str  # "valid" | "invalid" | "degraded"
    error_code: str | None = None
    error_detail: str | None = None
    trace_id: str | None = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_payload(
    action_type: str,
    payload_version: str,
    payload: dict[str, Any],
) -> ValidationResult:
    """Validate *payload* and return a ``ValidationResult``.

    On failure the result contains a degraded safe fallback payload
    so the caller can still persist the record without delivering
    broken content to the user.
    """
    trace_id = f"trace_{uuid.uuid4().hex[:12]}"

    # 1. Look up schema
    schema = get_schema(action_type, payload_version)
    if schema is None:
        msg = f"No schema for action_type={action_type!r} version={payload_version!r}"
        logger.warning("[%s] %s", trace_id, msg)
        return ValidationResult(
            valid=False,
            payload=_SAFE_FALLBACK.get(action_type, {"title": "暂不可用", "message": "系统内部错误"}),
            status="invalid",
            error_code="SCHEMA_NOT_FOUND",
            error_detail=msg,
            trace_id=trace_id,
        )

    # 2. Validate
    try:
        jsonschema.validate(instance=payload, schema=schema)
    except ValidationError as exc:
        short = str(exc.message)[:300]
        path = ".".join(str(p) for p in exc.absolute_path) or "(root)"
        logger.warning(
            "[%s] Payload validation failed at %s: %s", trace_id, path, short
        )
        return ValidationResult(
            valid=False,
            payload=_SAFE_FALLBACK.get(action_type, {"title": "暂不可用", "message": "系统内部错误"}),
            status="degraded",
            error_code="VALIDATION_FAILED",
            error_detail=f"{path}: {short}",
            trace_id=trace_id,
        )

    # 3. All good
    return ValidationResult(
        valid=True,
        payload=payload,
        status="valid",
        trace_id=trace_id,
    )
