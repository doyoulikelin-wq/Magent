from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserMeOut(BaseModel):
    id: str
    email: str
    created_at: datetime
    consent: dict
    settings: dict | None = None


class ConsentUpdateRequest(BaseModel):
    allow_ai_chat: bool | None = None
    allow_data_upload: bool | None = None


class ConsentOut(BaseModel):
    allow_ai_chat: bool
    allow_data_upload: bool
    version: str
    updated_at: datetime


# ── Subject-based login ──────────────────────────────────────


class SubjectInfo(BaseModel):
    subject_id: str
    cohort: str  # "cgm" | "liver"
    has_meals: bool
    has_glucose: bool
    display_name: str | None = None


class SubjectLoginRequest(BaseModel):
    subject_id: str = Field(min_length=2, max_length=30)
