from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class EnterDayResponse(BaseModel):
    session_id: str
    expires_at: datetime
    entered_at: datetime
    question_id: str
    question_title: str
    question_type: str          # "practical" | "theoretical"
    question_body: str          # Savol matni
    starter_code: str
    time_limit_secs: int
    is_readonly: bool
    previous_code: Optional[str] = None
    previous_note: Optional[str] = None
    previous_score: Optional[int] = None


class TypingStartRequest(BaseModel):
    timestamp: datetime


class AutosaveRequest(BaseModel):
    code: Optional[str] = None
    note_content: Optional[str] = None


class ViolationRequest(BaseModel):
    violation_type: str  # fullscreen_exit | tab_switch | paste_detected | devtools | multi_monitor


class ViolationResponse(BaseModel):
    violations_count: int
    max_allowed: int
    is_disqualified: bool
    message: str


class SubmitRequest(BaseModel):
    code: Optional[str] = None           # Amaliy savol uchun
    note_content: Optional[str] = None   # Nazariy savol uchun
    keystroke_count: Optional[int] = None


class SubmitResponse(BaseModel):
    result: str           # submitted | disqualified | manual_review
    score: int
    execution_ms: Optional[int] = None
    output: Optional[str] = None
    message: str


class MyDayStatus(BaseModel):
    day_id: Optional[str] = None
    day_number: int
    title: Optional[str]
    time_limit_secs: int
    is_today: bool
    is_locked: bool
    is_expired: bool
    is_completed: bool
    is_disqualified: bool
    score: Optional[int]
    opens_on: str


class ChallengeProgressResponse(BaseModel):
    challenge_id: str
    challenge_name: str
    total_days: int
    days: list[MyDayStatus]
    my_total_score: Optional[int]
