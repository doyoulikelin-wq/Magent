from datetime import datetime, timedelta, timezone

from app.services.glucose_service import compute_gaps_hours, compute_tir, variability_label


def test_compute_tir_basic():
    assert compute_tir([80, 100, 190, 65, 160]) == 60.0


def test_variability_label_thresholds():
    low = [100] * 20
    medium = [80, 130] * 10
    high = [50, 190] * 10

    assert variability_label(low) == "low"
    assert variability_label(medium) == "medium"
    assert variability_label(high) == "high"


def test_compute_gaps_hours_detects_missing_windows():
    base = datetime(2026, 2, 18, 12, 0, tzinfo=timezone.utc)
    points = [
        base,
        base + timedelta(minutes=5),
        base + timedelta(minutes=10),
        base + timedelta(minutes=50),
    ]
    gap = compute_gaps_hours(points)
    assert gap > 0
