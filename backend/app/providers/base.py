from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

from pydantic import BaseModel, Field


class MealVisionItem(BaseModel):
    name: str
    portion_text: str
    kcal: int


class MealVisionResult(BaseModel):
    items: list[MealVisionItem]
    total_kcal: int
    confidence: float = Field(ge=0, le=1)
    notes: str = ""


class ChatLLMResult(BaseModel):
    answer_markdown: str
    confidence: float = Field(ge=0, le=1)
    followups: list[str] = []
    safety_flags: list[str] = []


class LLMProvider(ABC):
    provider_name: str
    text_model: str
    vision_model: str

    @abstractmethod
    def analyze_image(self, image_url: str) -> MealVisionResult:
        raise NotImplementedError

    @abstractmethod
    def generate_text(self, context: dict, user_query: str) -> ChatLLMResult:
        raise NotImplementedError

    @abstractmethod
    def stream_text(self, context: dict, user_query: str) -> Iterator[str]:
        raise NotImplementedError
