from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.db.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    username = Column(String(100), nullable=False)
    avatar_url = Column(Text, nullable=True)
    is_admin = Column(Boolean, default=False)
    level = Column(Integer, default=1)
    total_score = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Challenge(Base):
    __tablename__ = "challenges"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    total_days = Column(Integer, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    prize_info = Column(Text, nullable=True)
    status = Column(String(20), default="draft")  # draft | active | ended
    max_violations = Column(Integer, default=3)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    days = relationship("ChallengeDay", back_populates="challenge", cascade="all, delete-orphan")


class ChallengeDay(Base):
    __tablename__ = "challenge_days"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    challenge_id = Column(UUID(as_uuid=True), ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False)
    day_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=True)
    time_limit_secs = Column(Integer, nullable=False, default=900)

    __table_args__ = (UniqueConstraint("challenge_id", "day_number", name="uq_challenge_day"),)

    challenge = relationship("Challenge", back_populates="days")
    questions = relationship("Question", back_populates="challenge_day", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    challenge_day_id = Column(UUID(as_uuid=True), ForeignKey("challenge_days.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(300), nullable=False)
    body_svg = Column(Text, nullable=False)           # Savol matni SVG formatida
    difficulty = Column(String(10), nullable=False)   # easy | medium | hard
    starter_code = Column(Text, default="")
    test_cases = Column(JSONB, nullable=False)         # [{"input": "...", "expected": "..."}]
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    challenge_day = relationship("ChallengeDay", back_populates="questions")


class UserQuestionAssignment(Base):
    __tablename__ = "user_question_assignments"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    challenge_day_id = Column(UUID(as_uuid=True), ForeignKey("challenge_days.id"), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id"), nullable=False)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "challenge_day_id", name="uq_user_day_assignment"),)

    question = relationship("Question")
    sessions = relationship("ExamSession", back_populates="assignment")


class ExamSession(Base):
    __tablename__ = "exam_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("user_question_assignments.id"), nullable=False)

    entered_at = Column(DateTime(timezone=True), server_default=func.now())
    typing_started_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    status = Column(String(20), default="active")
    # active | submitted | auto_submitted | disqualified | expired
    violations_count = Column(Integer, default=0)
    final_code = Column(Text, nullable=True)
    is_readonly = Column(Boolean, default=False)

    assignment = relationship("UserQuestionAssignment", back_populates="sessions")
    violations = relationship("ViolationLog", back_populates="session")


class ViolationLog(Base):
    __tablename__ = "violation_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("exam_sessions.id"), nullable=False)
    violation_type = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ExamSession", back_populates="violations")


class Submission(Base):
    __tablename__ = "submissions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("exam_sessions.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    challenge_day_id = Column(UUID(as_uuid=True), ForeignKey("challenge_days.id"), nullable=False)
    code = Column(Text, nullable=False)
    result = Column(String(20))     # pass | fail | error | timeout
    score = Column(Integer, default=0)
    execution_ms = Column(Integer, nullable=True)
    docker_output = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())


class ChallengeResult(Base):
    __tablename__ = "challenge_results"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    challenge_id = Column(UUID(as_uuid=True), ForeignKey("challenges.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    total_score = Column(Integer, default=0)
    days_completed = Column(Integer, default=0)
    final_rank = Column(Integer, nullable=True)
    is_winner = Column(Boolean, default=False)
    prize_received = Column(Boolean, default=False)
    finalized_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("challenge_id", "user_id", name="uq_challenge_user_result"),)
