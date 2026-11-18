from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel


class EnterDayResponse(BaseModel):
    session_id: str
    expires_at: datetime
    entered_at: datetime
    question_id: str
    question_title: str
    question_type: str          # "practical" | "quiz" | "theoretical"
    question_body: str          # Savol matni
    starter_code: str
    sample_tests: Optional[list[dict[str, Any]]] = None
    options: Optional[list[str]] = None
    time_limit_secs: int
    is_readonly: bool
    previous_code: Optional[str] = None
    previous_note: Optional[str] = None
    previous_score: Optional[int] = None
    violations_count: int = 0
    max_violations: int = 3


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
    selected_option: Optional[int] = None  # Quiz savol uchun (ko'rsatilgan indeks)
    keystroke_count: Optional[int] = None


class SubmitResponse(BaseModel):
    result: str           # pass | fail | error | timeout | manual_review | submitted
    score: int
    execution_ms: Optional[int] = None
    passed_tests: Optional[int] = None
    total_tests: Optional[int] = None
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
    my_rank: Optional[int] = None
    total_participants: Optional[int] = None


class RunCodeRequest(BaseModel):
    code: str
    input_data: Optional[str] = ""


class RunCodeResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    execution_ms: int
    timed_out: bool = False
    truncated: bool = False
