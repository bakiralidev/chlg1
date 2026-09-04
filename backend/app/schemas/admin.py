from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional
import uuid


# ─── Challenge ───────────────────────────────────────────────
class ChallengeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    total_days: int
    start_date: datetime
    prize_info: Optional[str] = None
    max_violations: int = 3


class ChallengeResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    total_days: int
    start_date: datetime
    prize_info: Optional[str]
    status: str
    max_violations: int
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Challenge Day ────────────────────────────────────────────
class DayCreate(BaseModel):
    challenge_id: str
    day_number: int
    title: Optional[str] = None
    time_limit_secs: int  # Admin belgilaydi (soniyada)


class DayResponse(BaseModel):
    id: str
    challenge_id: str
    day_number: int
    title: Optional[str]
    time_limit_secs: int

    class Config:
        from_attributes = True


# ─── Question ─────────────────────────────────────────────────
class TestCase(BaseModel):
    input: str
    expected: str


class QuestionCreate(BaseModel):
    challenge_day_id: str
    title: str
    body_svg: str          # SVG matn sifatida kiritiladi
    difficulty: str        # easy | medium | hard
    starter_code: str = ""
    test_cases: list[TestCase]

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v):
        if v not in ("easy", "medium", "hard"):
            raise ValueError("difficulty: easy, medium yoki hard bo'lishi kerak")
        return v


class QuestionResponse(BaseModel):
    id: str
    challenge_day_id: str
    title: str
    difficulty: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Stats ────────────────────────────────────────────────────
class ChallengeStats(BaseModel):
    challenge_id: str
    total_participants: int
    total_submissions: int
    days_with_questions: int
