from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    thread_id: str | None = None


class ChatResult(BaseModel):
    answer_markdown: str
    confidence: float = Field(ge=0, le=1)
    followups: list[str] = []
    safety_flags: list[str] = []
    used_context: dict
