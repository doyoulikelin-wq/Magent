from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.services import inference_service


@dataclass
class Point:
    ts: datetime
    glucose_mgdl: int


def test_infer_meal_time_returns_best_rising_point(monkeypatch):
    base = datetime(2026, 2, 18, 12, 0, tzinfo=timezone.utc)
    points = [
        Point(base + timedelta(minutes=i * 5), g)
        for i, g in enumerate([90, 92, 95, 100, 110, 125, 145, 160, 166, 170, 169, 168])
    ]

    monkeypatch.setattr(inference_service, "get_glucose_points", lambda *_: points)

    inferred, confidence = inference_service.infer_meal_time_from_glucose(db=None, user_id="u1", uploaded_at=base)

    assert inferred is not None
    assert 0 < confidence <= 1


def test_infer_meal_time_returns_none_when_not_enough_points(monkeypatch):
    base = datetime(2026, 2, 18, 12, 0, tzinfo=timezone.utc)
    points = [Point(base + timedelta(minutes=i * 5), 100 + i) for i in range(5)]
    monkeypatch.setattr(inference_service, "get_glucose_points", lambda *_: points)

    inferred, confidence = inference_service.infer_meal_time_from_glucose(db=None, user_id="u1", uploaded_at=base)

    assert inferred is None
    assert confidence == 0.0
