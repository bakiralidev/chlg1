from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class EnterDayResponse(BaseModel):
    session_id: str
    expires_at: datetime
    entered_at: datetime
    question_id: str
    question_title: str
    question_svg: str       # SVG matn
    starter_code: str
    time_limit_secs: int
    is_readonly: bool       # Avval yuborilgan bo'lsa True
    previous_code: Optional[str] = None   # is_readonly=True da yuborilgan kod
    previous_score: Optional[int] = None  # is_readonly=True da ball


class TypingStartRequest(BaseModel):
    timestamp: datetime


class AutosaveRequest(BaseModel):
    code: str


class ViolationRequest(BaseModel):
    violation_type: str  # fullscreen_exit | tab_switch | paste_detected | devtools | multi_monitor


class ViolationResponse(BaseModel):
    violations_count: int
    max_allowed: int
    is_disqualified: bool
    message: str


class SubmitRequest(BaseModel):
    code: str
    keystroke_count: Optional[int] = None


class SubmitResponse(BaseModel):
    result: str           # pass | fail | error | timeout | disqualified
    score: int
    execution_ms: Optional[int]
    output: Optional[str]
    message: str


class MyDayStatus(BaseModel):
    day_id: Optional[str] = None
    day_number: int
    title: Optional[str]
    time_limit_secs: int
    is_today: bool
    is_locked: bool        # Kelajakdagi kun
    is_expired: bool       # O'tib ketgan, hech narsa qilinmagan
    is_completed: bool     # Yuborilgan
    is_disqualified: bool
    score: Optional[int]   # Ertasi kuni ko'rinadi
    opens_on: str          # "2026-09-12" formatida


class ChallengeProgressResponse(BaseModel):
    challenge_id: str
    challenge_name: str
    total_days: int
    days: list[MyDayStatus]
    my_total_score: Optional[int]  # Faqat challenge tugagandan keyin
