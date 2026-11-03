from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, List
import uuid


# --- Challenge -----------------------------------------------
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


# --- Challenge Day --------------------------------------------
class DayCreate(BaseModel):
    challenge_id: str
    day_number: int
    title: Optional[str] = None
    time_limit_secs: int


class DayResponse(BaseModel):
    id: str
    challenge_id: str
    day_number: int
    title: Optional[str]
    time_limit_secs: int

    class Config:
        from_attributes = True


# --- Question -------------------------------------------------
class TestCase(BaseModel):
    input: str
    expected: str


class QuestionCreate(BaseModel):
    challenge_day_id: str
    title: str
    question_type: str = "practical"
    body_text: str
    difficulty: str
    starter_code: str = ""
    test_cases: Optional[List[TestCase]] = None

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v):
        if v not in ("easy", "medium", "hard"):
            raise ValueError("difficulty: easy, medium yoki hard bolishi kerak")
        return v

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, v):
        if v not in ("practical", "theoretical"):
            raise ValueError("question_type: practical yoki theoretical bolishi kerak")
        return v


class QuestionResponse(BaseModel):
    id: str
    challenge_day_id: str
    title: str
    question_type: str
    difficulty: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Stats ----------------------------------------------------
class ChallengeStats(BaseModel):
    challenge_id: str
    total_participants: int
    total_submissions: int
    days_with_questions: int


# --- AI Score Import ------------------------------------------
class AIScoreImportResult(BaseModel):
    total_rows: int
    matched_users: int
    imported_scores: int
    skipped: int
    errors: List[str]


# --- Manual Grading -------------------------------------------
class GradeRequest(BaseModel):
    score: int
    result: Optional[str] = 'graded'
    notes: Optional[str] = None
