"""Agent decision engine – Observe → Understand → Plan → Act.

Produces proactive briefings, pre-meal simulations, rescue cards,
and weekly reviews using real user data + feature snapshots.
All outputs are structured dicts ready for the chat / dog bubble.
"""

from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, func as sa_func
from sqlalchemy.orm import Session

from app.models.agent import ActionType, ActionStatus, AgentAction, AgentState
from app.models.feature import FeatureSnapshot
from app.models.glucose import GlucoseReading
from app.models.meal import Meal
from app.models.user_profile import UserProfile
from app.models.user_settings import UserSettings
from app.core.intervention import InterventionLevel, classify_risk, get_strategy

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════


def _latest_features(db: Session, user_id: uuid.UUID, window: str = "24h") -> dict:
    """Return the most recent FeatureSnapshot dict for a window."""
    snap = db.execute(
        select(FeatureSnapshot)
        .where(FeatureSnapshot.user_id == user_id, FeatureSnapshot.window == window)
        .order_by(FeatureSnapshot.computed_at.desc())
        .limit(1)
    ).scalars().first()
    return snap.features if snap else {}


def _recent_glucose(db: Session, user_id: uuid.UUID, hours: int = 2) -> list[dict]:
    """Return recent glucose readings as [{ts, v}]."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = db.execute(
        select(GlucoseReading.ts, GlucoseReading.glucose_mgdl)
        .where(GlucoseReading.user_id == user_id, GlucoseReading.ts >= since)
        .order_by(GlucoseReading.ts)
    ).all()
    return [{"ts": r.ts.isoformat(), "v": r.glucose_mgdl} for r in rows]


def _user_profile(db: Session, user_id: uuid.UUID) -> dict:
    profile = db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    ).scalars().first()
    if not profile:
        return {}
    return {
        "subject_id": profile.subject_id,
        "cohort": profile.cohort,
        "sex": profile.sex,
        "age": profile.age,
        "liver_risk_level": profile.liver_risk_level,
    }


def _user_strategy(db: Session, user_id: uuid.UUID):
    settings = db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    ).scalars().first()
    level = InterventionLevel(settings.intervention_level) if settings else InterventionLevel.L2
    return get_strategy(level)


def _save_action(
    db: Session,
    user_id: uuid.UUID,
    action_type: ActionType,
    payload: dict,
    evidence: dict,
    priority: str = "medium",
) -> AgentAction:
    action = AgentAction(
        user_id=user_id,
        action_type=action_type,
        payload=payload,
        reason_evidence=evidence,
        status=ActionStatus.valid,
        priority=priority,
        payload_version="1.0.0",
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


# ═══════════════════════════════════════════════════════════════
#  A. 今日代谢天气 (Daily Briefing / Metabolic Weather)
# ═══════════════════════════════════════════════════════════════


def generate_daily_briefing(db: Session, user_id: uuid.UUID) -> dict[str, Any]:
    """Build today's metabolic weather report.

    Returns structured dict with:
    - glucose_status: current trend, TIR
    - risk_windows: predicted high-risk time slots
    - today_goals: 1-2 actionable items
    - greeting: natural language summary for chat bubble
    """
    profile = _user_profile(db, user_id)
    feat_24h = _latest_features(db, user_id, "24h")
    feat_7d = _latest_features(db, user_id, "7d")
    recent = _recent_glucose(db, user_id, hours=4)

    # TIR / CV
    tir = feat_24h.get("tir_70_180", None)
    cv = feat_24h.get("cv", None)
    glucose_mean = feat_24h.get("glucose_mean", None)
    n_readings = feat_24h.get("n_readings", 0)

    # Trend from recent readings
    trend = "unknown"
    current_mgdl = None
    if len(recent) >= 3:
        last_vals = [r["v"] for r in recent[-6:]]
        current_mgdl = last_vals[-1]
        slope = (last_vals[-1] - last_vals[0]) / max(len(last_vals), 1)
        if slope > 2:
            trend = "rising"
        elif slope < -2:
            trend = "falling"
        else:
            trend = "stable"

    # Risk windows heuristic: check 7d pattern for high-meal times
    feat_28d = _latest_features(db, user_id, "28d")
    kcal_slope = feat_28d.get("kcal_response_slope")
    risk_windows = []
    # Simple rule: if afternoon/evening kcal_response_slope is high, flag dinner
    if kcal_slope and float(kcal_slope) > 0.05:
        risk_windows.append({"start": "17:00", "end": "20:00", "risk": "medium",
                             "reason": f"热量-血糖斜率偏高 ({float(kcal_slope):.3f})"})

    # Goals
    goals = []
    if tir is not None and tir < 0.7:
        goals.append(f"今日目标：提升 TIR 至 70%+（当前 {tir * 100:.0f}%）")
    if cv is not None and cv > 0.3:
        goals.append("减少血糖波动：午餐/晚餐前后多走动 10 分钟")
    if not goals:
        goals.append("保持良好状态！继续维持健康节奏 🎉")

    # Natural language greeting
    is_liver = profile.get("cohort") == "liver"
    greeting_parts = []
    if current_mgdl:
        greeting_parts.append(f"当前血糖 {current_mgdl} mg/dL（{trend_zh(trend)}）")
    if tir is not None:
        greeting_parts.append(f"24h TIR {tir * 100:.0f}%")
    if n_readings == 0:
        greeting_parts.append("还没有今日血糖数据，记得佩戴好传感器哦")
    if is_liver and risk_windows:
        greeting_parts.append("今天晚餐时段注意控制碳水摄入")
    if not greeting_parts:
        greeting_parts.append("你好呀，今天也要加油哦！")

    greeting = "🌤️ " + "；".join(greeting_parts) + "。"

    briefing = {
        "type": "daily_briefing",
        "greeting": greeting,
        "glucose_status": {
            "current_mgdl": current_mgdl,
            "trend": trend,
            "tir_24h": round(tir * 100, 1) if tir is not None else None,
            "cv_24h": round(cv * 100, 1) if cv is not None else None,
            "mean_24h": round(glucose_mean, 1) if glucose_mean is not None else None,
        },
        "risk_windows": risk_windows,
        "today_goals": goals,
        "evidence": {
            "window": "24h",
            "n_readings": n_readings,
            "features_used": ["tir_70_180", "cv", "glucose_mean", "kcal_response_slope"],
        },
    }

    # Persist as AgentAction
    _save_action(db, user_id, ActionType.daily_plan, briefing, briefing["evidence"])

    return briefing


# ═══════════════════════════════════════════════════════════════
#  B. 吃前预演 (Pre-Meal Simulator)
# ═══════════════════════════════════════════════════════════════


def simulate_pre_meal(
    db: Session,
    user_id: uuid.UUID,
    kcal: float,
    meal_time: str = "now",
) -> dict[str, Any]:
    """Predict post-meal glucose response and suggest alternatives.

    Uses kcal_response_slope (from 28d features) as a simple linear model:
        predicted_peak_delta = slope * kcal
    """
    feat_28d = _latest_features(db, user_id, "28d")
    feat_24h = _latest_features(db, user_id, "24h")
    slope = feat_28d.get("kcal_response_slope", 0.05)  # default conservative slope
    slope_std = feat_28d.get("kcal_response_slope_std", 0.02)
    baseline = feat_24h.get("glucose_mean", 100)

    if slope is None or slope == 0:
        slope = 0.05
    if slope_std is None:
        slope_std = 0.02

    slope = float(slope)
    slope_std = float(slope_std)
    baseline = float(baseline)

    # Prediction
    peak_delta = slope * kcal
    peak_glucose = baseline + peak_delta
    time_to_peak_min = min(90, max(30, int(45 + kcal * 0.03)))  # rough heuristic
    auc_estimate = peak_delta * time_to_peak_min * 0.6  # rough triangle area

    # Confidence based on sample size
    n_meals = feat_28d.get("n_meals_for_slope", 0)
    confidence = min(0.9, max(0.3, 0.3 + 0.05 * (n_meals or 0)))

    # Alternatives
    alternatives = []
    if kcal > 400:
        reduced_kcal = kcal * 0.8
        alt_peak = baseline + slope * reduced_kcal
        alternatives.append({
            "id": "reduce_20",
            "label": f"减少 20% 主食 → 约 {reduced_kcal:.0f} kcal",
            "expected_delta_peak": round(alt_peak - peak_glucose, 1),
        })
    alternatives.append({
        "id": "walk_10",
        "label": "餐后步行 10 分钟",
        "expected_delta_peak": round(-peak_delta * 0.15, 1),
    })
    alternatives.append({
        "id": "delay_30",
        "label": "延后 30 分钟进餐",
        "expected_delta_peak": round(-peak_delta * 0.1, 1),
    })

    result = {
        "type": "pre_meal_sim",
        "title": f"吃前预演：{kcal:.0f} kcal",
        "meal_input": {"kcal": kcal, "meal_time": meal_time},
        "prediction": {
            "peak_glucose": round(peak_glucose, 1),
            "peak_delta": round(peak_delta, 1),
            "time_to_peak_min": time_to_peak_min,
            "auc_estimate": round(auc_estimate, 1),
            "baseline": round(baseline, 1),
            "confidence": round(confidence, 2),
        },
        "alternatives": alternatives,
        "evidence": {
            "slope": round(slope, 4),
            "slope_std": round(slope_std, 4),
            "n_meals_for_slope": n_meals,
            "window": "28d",
            "note": "基于近 28 天热量-血糖响应斜率的线性预测",
        },
    }

    _save_action(db, user_id, ActionType.pre_meal_sim, result, result["evidence"])
    return result


# ═══════════════════════════════════════════════════════════════
#  C. 吃后补救 (Post-Meal Rescue)
# ═══════════════════════════════════════════════════════════════


def check_rescue_needed(db: Session, user_id: uuid.UUID) -> dict[str, Any] | None:
    """Check if a rescue suggestion should fire.

    Triggers when recent glucose slope indicates rapid rise (>3 mg/dL per 5-min).
    Returns a rescue card or None if all is calm.
    """
    recent = _recent_glucose(db, user_id, hours=1)
    if len(recent) < 4:
        return None

    # Compute slope over last ~20 min (4 readings at 5-min intervals)
    last_few = recent[-6:]
    vals = [r["v"] for r in last_few]
    slope_per_5min = (vals[-1] - vals[0]) / max(len(vals) - 1, 1)
    current = vals[-1]

    # Check threshold
    strategy = _user_strategy(db, user_id)
    threshold = 3.0 if strategy.trigger_min_risk.value == "medium" else 5.0

    if slope_per_5min < threshold and current < 180:
        return None  # All good

    # Build rescue card
    risk_level = "high" if current > 200 or slope_per_5min > 6 else "medium"
    steps = [
        {"id": "walk", "label": "立即步行 15 分钟", "duration_min": 15},
        {"id": "water", "label": "喝一杯水（300-500ml）", "duration_min": 5},
    ]
    if risk_level == "high":
        steps.append({"id": "next_meal", "label": "下一餐减半碳水", "duration_min": None})

    expected_drop = slope_per_5min * 0.3  # rough estimate
    rescue = {
        "type": "rescue",
        "title": "⚠️ 血糖快速上升中",
        "risk_level": risk_level,
        "trigger_evidence": [
            f"近期斜率: {slope_per_5min:+.1f} mg/dL per 5min",
            f"当前血糖: {current} mg/dL",
        ],
        "steps": steps,
        "expected_effect": {
            "delta_peak_low": round(-expected_drop * 0.5, 1),
            "delta_peak_high": round(-expected_drop * 1.5, 1),
        },
        "checkpoints_min": [30, 60, 120],
        "evidence": {
            "slope_per_5min": round(slope_per_5min, 2),
            "current_mgdl": current,
            "n_points": len(last_few),
            "window": "last_30min",
        },
    }

    _save_action(db, user_id, ActionType.rescue, rescue, rescue["evidence"], priority="high")
    return rescue


# ═══════════════════════════════════════════════════════════════
#  D. 周目标代理 (Weekly Review)
# ═══════════════════════════════════════════════════════════════


def generate_weekly_review(db: Session, user_id: uuid.UUID) -> dict[str, Any]:
    """Build a weekly review comparing last 7d vs previous 7d."""
    feat_7d = _latest_features(db, user_id, "7d")
    feat_28d = _latest_features(db, user_id, "28d")

    tir_7d = feat_7d.get("tir_70_180")
    cv_7d = feat_7d.get("cv")
    auc_7d = feat_7d.get("auc_above_100")
    meal_count = feat_7d.get("meal_count", 0)
    avg_kcal = feat_7d.get("avg_kcal")
    max_kcal = feat_7d.get("max_kcal")

    tir_28d = feat_28d.get("tir_70_180")

    # Highlights
    highlights = []
    if tir_7d is not None:
        highlights.append(f"本周 TIR: {tir_7d * 100:.0f}%")
        if tir_28d is not None:
            delta = (tir_7d - tir_28d) * 100
            if delta > 2:
                highlights.append(f"✅ TIR 较上月提升 {delta:.1f}%")
            elif delta < -2:
                highlights.append(f"⚠️ TIR 较上月下降 {abs(delta):.1f}%")
    if cv_7d is not None:
        highlights.append(f"血糖波动 CV: {cv_7d * 100:.0f}%")
    if max_kcal and max_kcal > 800:
        highlights.append(f"⚠️ 本周最大单餐: {max_kcal:.0f} kcal（疑似暴食）")

    # Next week goal
    next_focus = None
    target = None
    if tir_7d is not None and tir_7d < 0.75:
        next_focus = "提升 TIR 至 75%"
        target = {
            "metric": "tir_70_180",
            "baseline": round(tir_7d * 100, 1),
            "goal": 75.0,
            "unit": "%",
            "window_days": 7,
        }
    elif cv_7d is not None and cv_7d > 0.30:
        next_focus = "降低血糖波动"
        target = {
            "metric": "cv",
            "baseline": round(cv_7d * 100, 1),
            "goal": 30.0,
            "unit": "% CV",
            "window_days": 7,
        }
    else:
        next_focus = "保持当前良好水平"

    tasks = []
    if avg_kcal and avg_kcal > 600:
        tasks.append("每餐控制在 500 kcal 以内")
    tasks.append("每天餐后步行 10 分钟")
    if tir_7d and tir_7d < 0.7:
        tasks.append("减少晚间高碳水零食")

    review = {
        "type": "weekly_review",
        "title": "📊 本周健康复盘",
        "highlights": highlights,
        "next_focus": next_focus,
        "target": target,
        "tasks": tasks,
        "evidence": {
            "window": "7d",
            "features_used": ["tir_70_180", "cv", "auc_above_100", "meal_count", "avg_kcal", "max_kcal"],
            "meal_count": meal_count,
        },
    }

    _save_action(db, user_id, ActionType.weekly_goal, review, review["evidence"])
    return review


# ═══════════════════════════════════════════════════════════════
#  E. 主动消息 (Proactive Dog Message)
# ═══════════════════════════════════════════════════════════════


def get_proactive_message(db: Session, user_id: uuid.UUID) -> dict[str, Any]:
    """Generate the dog's proactive bubble message.

    Combines:
    - Quick glucose status
    - Any active rescue alert
    - Today's top goal
    Returns a short message + optional action cards.
    """
    profile = _user_profile(db, user_id)
    feat_24h = _latest_features(db, user_id, "24h")
    recent = _recent_glucose(db, user_id, hours=2)

    # Check for active rescue condition
    rescue = check_rescue_needed(db, user_id)

    # Build message
    parts = []
    cards: list[dict] = []

    if rescue:
        parts.append(rescue["title"])
        cards.append(rescue)
    else:
        tir = feat_24h.get("tir_70_180")
        n = feat_24h.get("n_readings", 0)
        if n == 0:
            parts.append("今天还没有血糖数据哦，记得看看传感器～")
        elif recent:
            current = recent[-1]["v"]
            if current > 180:
                parts.append(f"血糖有点高了 ({current} mg/dL)，要不要走一走？")
            elif current < 70:
                parts.append(f"血糖偏低 ({current} mg/dL)，吃点东西补充能量吧！")
            else:
                parts.append(f"血糖 {current} mg/dL，状态不错 👍")
        if tir is not None:
            parts.append(f"TIR {tir * 100:.0f}%")

    # Combine
    if not parts:
        is_liver = profile.get("cohort") == "liver"
        if is_liver:
            parts.append("点我聊聊你的体检指标和饮食建议～")
        else:
            parts.append("点我和我聊聊健康吧～")

    return {
        "message": "；".join(parts),
        "cards": cards,
        "has_rescue": rescue is not None,
    }


# ═══════════════════════════════════════════════════════════════
#  Utility
# ═══════════════════════════════════════════════════════════════

def trend_zh(trend: str) -> str:
    return {"rising": "上升中", "falling": "下降中", "stable": "平稳", "unknown": "未知"}.get(trend, trend)
