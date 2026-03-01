from __future__ import annotations

from typing import Iterator

from app.core.config import settings
from app.providers.base import ChatLLMResult, LLMProvider, MealVisionItem, MealVisionResult


class GeminiProvider(LLMProvider):
    provider_name = "gemini"
    text_model = settings.GEMINI_MODEL_TEXT
    vision_model = settings.GEMINI_MODEL_VISION

    def analyze_image(self, image_url: str) -> MealVisionResult:
        # TODO: replace with official Gemini generateContent multimodal call.
        items = [MealVisionItem(name="mixed meal", portion_text="1 plate", kcal=520)]
        return MealVisionResult(items=items, total_kcal=520, confidence=0.42, notes=f"fallback for {image_url}")

    def generate_text(self, context: dict, user_query: str) -> ChatLLMResult:
        _ = context
        return ChatLLMResult(
            answer_markdown=f"[Gemini fallback] {user_query}",
            confidence=0.38,
            followups=["要不要我结合 7 天趋势再分析？"],
            safety_flags=[],
        )

    def stream_text(self, context: dict, user_query: str) -> Iterator[str]:
        result = self.generate_text(context, user_query)
        for part in result.answer_markdown.split(" "):
            yield part + " "
