from __future__ import annotations

from typing import Iterator

from app.providers.base import ChatLLMResult, LLMProvider, MealVisionItem, MealVisionResult


class MockProvider(LLMProvider):
    provider_name = "mock"
    text_model = "mock-text"
    vision_model = "mock-vision"

    def analyze_image(self, image_url: str) -> MealVisionResult:
        _ = image_url
        items = [
            MealVisionItem(name="米饭", portion_text="1 碗", kcal=260),
            MealVisionItem(name="鸡胸肉", portion_text="100g", kcal=165),
            MealVisionItem(name="蔬菜", portion_text="1 份", kcal=80),
        ]
        total = sum(i.kcal for i in items)
        return MealVisionResult(items=items, total_kcal=total, confidence=0.72, notes="mock estimate")

    def generate_text(self, context: dict, user_query: str) -> ChatLLMResult:
        meals_today = context.get("meals_today", [])
        kcal_today = context.get("data_quality", {}).get("kcal_today", 0)
        answer = (
            f"你问的是：{user_query}\\n\\n"
            f"基于今日数据：共记录 {len(meals_today)} 次用餐，累计约 {kcal_today} kcal。"
            "建议结合餐后 1-2 小时血糖变化观察高碳水餐次。"
        )
        return ChatLLMResult(
            answer_markdown=answer,
            confidence=0.66,
            followups=["要不要我按今天每餐给出更细的建议？", "需要我比较 24h 和 7d 的波动差异吗？"],
            safety_flags=[],
        )

    def stream_text(self, context: dict, user_query: str) -> Iterator[str]:
        result = self.generate_text(context, user_query)
        for chunk in result.answer_markdown.split("\n"):
            yield chunk + "\n"
