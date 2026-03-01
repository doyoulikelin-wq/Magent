from dataclasses import dataclass
from datetime import datetime, timezone

from app.services import context_builder


@dataclass
class MealObj:
    meal_ts: datetime
    kcal: int
    tags: list[str]
    meal_ts_source: type("src", (), {"value": "user_confirmed"})
    photo_id: str | None = None


@dataclass
class SymptomObj:
    ts: datetime
    severity: int
    text: str


class _FakeResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return self._items

    def first(self):
        return self._items[0] if self._items else None


class FakeDB:
    def __init__(self, meals, symptoms):
        self.calls = 0
        self.meals = meals
        self.symptoms = symptoms

    def execute(self, _stmt):
        self.calls += 1
        # calls 1=meals(.all), 2=symptoms(.all), 3+=feature/profile(.first)
        if self.calls == 1:
            return _FakeResult(self.meals)
        elif self.calls == 2:
            return _FakeResult(self.symptoms)
        else:
            return _FakeResult([])


def test_build_user_context(monkeypatch):
    now = datetime(2026, 2, 18, 12, 0, tzinfo=timezone.utc)
    meal = MealObj(now, 500, ["high_carb"], type("src", (), {"value": "user_confirmed"}), None)
    symptom = SymptomObj(now, 2, "胃胀")

    monkeypatch.setattr(context_builder, "get_glucose_summary", lambda *_: {
        "window": "24h",
        "avg": 110,
        "min": 80,
        "max": 160,
        "tir_70_180_pct": 90,
        "variability": "medium",
        "gaps_hours": 1.0,
    })

    db = FakeDB([meal], [symptom])
    context = context_builder.build_user_context(db, user_id="u1")

    assert "glucose_summary" in context
    assert context["data_quality"]["kcal_today"] == 500
    assert len(context["meals_today"]) == 1
