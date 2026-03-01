"""Intervention level definitions and trigger strategy parameters.

Each level defines thresholds and limits used by the Agent to decide
when and how aggressively to send notifications / rescue cards.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class InterventionLevel(str, enum.Enum):
    L1 = "L1"  # 温和
    L2 = "L2"  # 标准 (default)
    L3 = "L3"  # 积极


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


# ---------------------------------------------------------------------------
# Risk thresholds (configurable, same for all levels)
# ---------------------------------------------------------------------------

RISK_THRESHOLDS: dict[RiskLevel, tuple[float, float]] = {
    RiskLevel.low: (0.0, 0.40),
    RiskLevel.medium: (0.40, 0.70),
    RiskLevel.high: (0.70, 1.0),
}


def classify_risk(score: float) -> RiskLevel:
    """Map a 0-1 risk score to a named level."""
    if score >= 0.70:
        return RiskLevel.high
    if score >= 0.40:
        return RiskLevel.medium
    return RiskLevel.low


# ---------------------------------------------------------------------------
# Per-level trigger strategy parameters
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TriggerStrategy:
    """Immutable parameter bundle for one intervention level."""

    level: InterventionLevel

    # Which risk levels trigger an action
    trigger_min_risk: RiskLevel

    # Daily proactive reminder cap
    daily_reminder_limit: int

    # Max reminders per single meal event
    per_meal_reminder_limit: int

    # Number of suggested action items
    suggestion_count_min: int
    suggestion_count_max: int

    # Review/debrief behaviour
    review_required: str  # "optional" | "recommended" | "default"

    # Consecutive-anomaly auto-escalation
    escalation_consecutive_days: int | None  # None = no auto-escalation


STRATEGIES: dict[InterventionLevel, TriggerStrategy] = {
    InterventionLevel.L1: TriggerStrategy(
        level=InterventionLevel.L1,
        trigger_min_risk=RiskLevel.high,
        daily_reminder_limit=1,
        per_meal_reminder_limit=1,
        suggestion_count_min=1,
        suggestion_count_max=1,
        review_required="optional",
        escalation_consecutive_days=None,
    ),
    InterventionLevel.L2: TriggerStrategy(
        level=InterventionLevel.L2,
        trigger_min_risk=RiskLevel.medium,
        daily_reminder_limit=2,
        per_meal_reminder_limit=2,
        suggestion_count_min=1,
        suggestion_count_max=2,
        review_required="recommended",
        escalation_consecutive_days=2,
    ),
    InterventionLevel.L3: TriggerStrategy(
        level=InterventionLevel.L3,
        trigger_min_risk=RiskLevel.medium,
        daily_reminder_limit=4,
        per_meal_reminder_limit=3,
        suggestion_count_min=2,
        suggestion_count_max=3,
        review_required="default",
        escalation_consecutive_days=1,
    ),
}


def get_strategy(level: InterventionLevel) -> TriggerStrategy:
    return STRATEGIES[level]
