from datetime import datetime

from pydantic import BaseModel, Field


class SymptomCreate(BaseModel):
    ts: datetime
    severity: int = Field(ge=0, le=5)
    text: str = Field(min_length=1, max_length=2000)


class SymptomOut(BaseModel):
    id: str
    ts: datetime
    severity: int
    text: str
