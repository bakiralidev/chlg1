import argparse
import asyncio
import json
import sys
import uuid
from collections import defaultdict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.database import async_session_maker  # noqa: E402
from app.models.models import ChallengeDay, Question  # noqa: E402
from app.services.sandbox_service import run_code_in_sandbox  # noqa: E402
from app.services.scoring import get_question_tests  # noqa: E402


async def validate_from_json(json_path: Path) -> int:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    day_counts: dict[int, int] = defaultdict(int)
    day_times: dict[int, list[int]] = defaultdict(list)
    failed: list[str] = []

    for idx, item in enumerate(data, start=1):
        day_num = item.get("day_number", 0)
        day_counts[day_num] += 1
        if item.get("question_type") != "practical":
            continue

        ref_code = item.get("reference_solution")
        if not ref_code:
            failed.append(f"Kun {day_num} '{item.get('title')}': reference_solution yo'q")
            continue

        tests = list(item.get("sample_tests") or []) + list(item.get("hidden_tests") or [])
        res = await run_code_in_sandbox(ref_code, tests)
        day_times[day_num].append(res["execution_ms"])
        if res["passed"] != res["total"]:
            failed.append(
                f"Kun {day_num} '{item.get('title')}': {res['passed']}/{res['total']} test o'tdi ({res['status']})"
            )

    _print_report(day_counts, day_times, failed)
    return 1 if failed else 0


async def validate_from_db(challenge_id: str) -> int:
    ch_uuid = uuid.UUID(challenge_id)
    day_counts: dict[int, int] = defaultdict(int)
    day_times: dict[int, list[int]] = defaultdict(list)
    failed: list[str] = []

    async with async_session_maker() as db:
        days_res = await db.execute(
            select(ChallengeDay)
            .where(ChallengeDay.challenge_id == ch_uuid)
            .order_by(ChallengeDay.day_number)
        )
        days = days_res.scalars().all()
        for day in days:
            q_res = await db.execute(select(Question).where(Question.challenge_day_id == day.id))
            questions = q_res.scalars().all()
            day_counts[day.day_number] = len(questions)
            for q in questions:
                if q.question_type != "practical":
                    continue
                if not q.reference_solution:
                    failed.append(f"Kun {day.day_number} '{q.title}': reference_solution yo'q")
                    continue
                samples, hidden = get_question_tests(q)
                res = await run_code_in_sandbox(q.reference_solution, samples + hidden)
                day_times[day.day_number].append(res["execution_ms"])
                if res["passed"] != res["total"]:
                    failed.append(
                        f"Kun {day.day_number} '{q.title}': {res['passed']}/{res['total']} test o'tdi ({res['status']})"
                    )

    _print_report(day_counts, day_times, failed)
    return 1 if failed else 0


def _print_report(day_counts: dict[int, int], day_times: dict[int, list[int]], failed: list[str]) -> None:
    print("\n=== Savollar Tekshiruv Hisoboti ===")
    for day_num in sorted(day_counts.keys()):
        times = day_times.get(day_num, [])
        avg_ms = round(sum(times) / len(times)) if times else 0
        print(f"  Kun {day_num:02d}: {day_counts[day_num]} ta savol | o'rtacha vaqt: {avg_ms} ms")

    if failed:
        print("\nXato savollar:")
        for f in failed:
            print(f"  - {f}")
    else:
        print("\nBarcha amaliy savollar reference_solution testlaridan muvaffaqiyatli o'tdi.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate practical questions against runner.")
    parser.add_argument("--challenge-id", help="Challenge UUID (bazadan tekshirish)")
    parser.add_argument("--file", type=Path, help="JSON fayldan tekshirish")
    parser.add_argument("--runner-url", help="Runner URL ni almashtirish")
    args = parser.parse_args()

    if args.runner_url:
        settings.RUNNER_URL = args.runner_url

    if args.file:
        rc = asyncio.run(validate_from_json(args.file))
    elif args.challenge_id:
        rc = asyncio.run(validate_from_db(args.challenge_id))
    else:
        parser.error("--challenge-id yoki --file dan birini bering")
        return
    sys.exit(rc)


if __name__ == "__main__":
    main()
