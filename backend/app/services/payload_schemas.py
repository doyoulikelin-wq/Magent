"""JSON Schema definitions for each AgentAction.payload type.

Schemas follow the structure defined in devlog §11.2.2.
When a new ``payload_version`` introduces breaking changes,
add a new entry keyed by ``(action_type, major_version)``.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# pre_meal_sim  v1
# ---------------------------------------------------------------------------

PRE_MEAL_SIM_V1 = {
    "type": "object",
    "required": ["title", "meal_input", "prediction", "alternatives"],
    "properties": {
        "title": {"type": "string"},
        "meal_input": {
            "type": "object",
            "required": ["kcal", "meal_time"],
            "properties": {
                "kcal": {"type": "number", "minimum": 0},
                "meal_time": {"type": "string", "format": "date-time"},
            },
        },
        "prediction": {
            "type": "object",
            "required": ["peak_glucose", "time_to_peak_min", "auc_0_120"],
            "properties": {
                "peak_glucose": {"type": "number"},
                "time_to_peak_min": {"type": "number", "minimum": 0},
                "auc_0_120": {"type": "number"},
                "liver_load_score": {"type": "number", "minimum": 0, "maximum": 1},
            },
        },
        "alternatives": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "label", "expected_delta_peak"],
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "expected_delta_peak": {"type": "number"},
                },
            },
        },
    },
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# post_meal_rescue (rescue)  v1
# ---------------------------------------------------------------------------

RESCUE_V1 = {
    "type": "object",
    "required": ["title", "risk_level", "trigger_evidence", "steps", "expected_effect"],
    "properties": {
        "title": {"type": "string"},
        "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
        "trigger_evidence": {
            "type": "array",
            "items": {"type": "string"},
        },
        "steps": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "label"],
                "properties": {
                    "id": {"type": "string"},
                    "label": {"type": "string"},
                    "duration_min": {"type": "number", "minimum": 0},
                },
            },
        },
        "expected_effect": {
            "type": "object",
            "required": ["delta_peak_low", "delta_peak_high"],
            "properties": {
                "delta_peak_low": {"type": "number"},
                "delta_peak_high": {"type": "number"},
            },
        },
        "followup": {
            "type": "object",
            "properties": {
                "checkpoints_min": {
                    "type": "array",
                    "items": {"type": "number"},
                },
            },
        },
        "expires_at": {"type": "string", "format": "date-time"},
    },
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# daily_plan  v1
# ---------------------------------------------------------------------------

DAILY_PLAN_V1 = {
    "type": "object",
    "required": ["title", "risk_windows", "today_goals"],
    "properties": {
        "title": {"type": "string"},
        "risk_windows": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["start", "end", "risk"],
                "properties": {
                    "start": {"type": "string"},
                    "end": {"type": "string"},
                    "risk": {"type": "string", "enum": ["low", "medium", "high"]},
                },
            },
        },
        "today_goals": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# weekly_goal  v1
# ---------------------------------------------------------------------------

WEEKLY_GOAL_V1 = {
    "type": "object",
    "required": ["title", "focus", "target", "tasks"],
    "properties": {
        "title": {"type": "string"},
        "focus": {"type": "string"},
        "target": {
            "type": "object",
            "required": ["metric", "baseline", "goal", "unit", "window_days"],
            "properties": {
                "metric": {"type": "string"},
                "baseline": {"type": "number"},
                "goal": {"type": "number"},
                "unit": {"type": "string"},
                "window_days": {"type": "integer", "minimum": 1},
            },
        },
        "tasks": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# Registry: (action_type, major_version) -> schema
# ---------------------------------------------------------------------------

SCHEMA_REGISTRY: dict[tuple[str, int], dict] = {
    ("pre_meal_sim", 1): PRE_MEAL_SIM_V1,
    ("rescue", 1): RESCUE_V1,
    ("daily_plan", 1): DAILY_PLAN_V1,
    ("weekly_goal", 1): WEEKLY_GOAL_V1,
}


def get_schema(action_type: str, payload_version: str) -> dict | None:
    """Look up the JSON schema for a given action_type + semver version.

    Returns ``None`` if no schema is registered for the major version.
    """
    try:
        major = int(payload_version.split(".")[0])
    except (ValueError, IndexError):
        return None
    return SCHEMA_REGISTRY.get((action_type, major))
