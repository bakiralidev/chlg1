import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    login: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=255)


class SetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Parol kamida 8 belgidan iborat bo'lishi kerak")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Parolda kamida bitta harf bo'lishi kerak")
        if not re.search(r"\d", v):
            raise ValueError("Parolda kamida bitta raqam bo'lishi kerak")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    login: str
    username: str
    full_name: Optional[str] = None
    is_admin: bool
    status: str
    must_change_password: bool
    consent_version: Optional[int] = None
    rules_version: int
    needs_consent: bool
