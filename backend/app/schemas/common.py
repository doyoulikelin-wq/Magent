from pydantic import BaseModel


class APIError(BaseModel):
    error_code: str
    message: str
    details: dict | None = None
    trace_id: str | None = None
