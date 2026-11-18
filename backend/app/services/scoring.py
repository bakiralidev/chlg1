import random
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Question, Submission, User
from app.services.sandbox_service import run_code_in_sandbox


def get_question_tests(question: Question) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (sample_tests, hidden_tests) for a practical question."""
    samples = list(question.sample_tests or [])
    hidden = list(question.hidden_tests or [])
    if not samples and not hidden and question.test_cases:
        hidden = list(question.test_cases)
    return samples, hidden


def shuffle_quiz_options(
    options: list[str],
    user_id: Any,
    question_id: Any,
) -> tuple[list[str], list[int]]:
    """
    Deterministically shuffle quiz options per (user_id, question_id).
    Returns (shuffled_options, index_map) where index_map[displayed_idx] == original_idx.
    """
    indices = list(range(len(options)))
    rng = random.Random(f"{user_id}:{question_id}")
    rng.shuffle(indices)
    shuffled = [options[i] for i in indices]
    return shuffled, indices


async def evaluate_practical(code: str, question: Question) -> dict[str, Any]:
    """Evaluate practical code submission against sample + hidden tests on 0-100 scale."""
    samples, hidden = get_question_tests(question)
    all_tests = samples + hidden

    if not all_tests:
        return {
            "score": 0,
            "result": "manual_review",
            "passed": 0,
            "total": 0,
            "execution_ms": 0,
            "output": "[]",
        }

    sandbox_res = await run_code_in_sandbox(code or "", all_tests)
    passed = sandbox_res["passed"]
    total = sandbox_res["total"]
    score = round((passed / total) * 100) if total > 0 else 0

    return {
        "score": score,
        "result": sandbox_res["status"],
        "passed": passed,
        "total": total,
        "execution_ms": sandbox_res["execution_ms"],
        "output": sandbox_res["output"],
    }


def evaluate_quiz(
    selected_display_idx: Optional[int],
    user_id: Any,
    question: Question,
) -> dict[str, Any]:
    """Evaluate quiz submission using deterministic option mapping. 100 or 0."""
    options = list(question.options or [])
    if selected_display_idx is None or not options or question.correct_option is None:
        return {
            "score": 0,
            "result": "fail",
            "original_selected": None,
        }

    if selected_display_idx < 0 or selected_display_idx >= len(options):
        return {
            "score": 0,
            "result": "fail",
            "original_selected": None,
        }

    _, index_map = shuffle_quiz_options(options, user_id, question.id)
    original_selected = index_map[selected_display_idx]
    is_correct = original_selected == question.correct_option
    return {
        "score": 100 if is_correct else 0,
        "result": "pass" if is_correct else "fail",
        "original_selected": original_selected,
    }


async def recalculate_total(db: AsyncSession, user_id: Any) -> int:
    """
    Single source of truth for user.total_score:
    sum of all submissions.score for the user (excludes participant_ai_scores).
    """
    total_res = await db.execute(
        select(func.coalesce(func.sum(Submission.score), 0)).where(
            Submission.user_id == user_id
        )
    )
    total = int(total_res.scalar() or 0)

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if user is not None:
        user.total_score = total
    await db.flush()
    return total
