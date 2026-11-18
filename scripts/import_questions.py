import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402
from app.db.database import async_session_maker  # noqa: E402
from app.models.models import ChallengeDay, Question  # noqa: E402

VALID_TYPES = {"practical", "quiz", "theoretical"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def validate_question_item(item: dict, idx: int, available_days: set[int]) -> list[str]:
    errors: list[str] = []
    prefix = f"Savol #{idx + 1}"

    for req_field in ("day_number", "title", "question_type", "body_text", "difficulty"):
        if req_field not in item or item[req_field] in (None, ""):
            errors.append(f"{prefix}: '{req_field}' majburiy maydon yo'q")

    day_num = item.get("day_number")
    if isinstance(day_num, int) and day_num not in available_days:
        errors.append(f"{prefix}: day_number={day_num} challengedagi kunlar orasida topilmadi")

    q_type = item.get("question_type")
    if q_type and q_type not in VALID_TYPES:
        errors.append(f"{prefix}: noto'g'ri question_type '{q_type}'")

    diff = item.get("difficulty")
    if diff and diff not in VALID_DIFFICULTIES:
        errors.append(f"{prefix}: noto'g'ri difficulty '{diff}'")

    if q_type == "quiz":
        options = item.get("options")
        correct = item.get("correct_option")
        if not isinstance(options, list) or len(options) < 2:
            errors.append(f"{prefix}: quiz uchun kamida 2 ta variant (options) kerak")
        elif not isinstance(correct, int) or correct < 0 or correct >= len(options):
            errors.append(f"{prefix}: correct_option 0..{len(options) - 1} oralig'ida bo'lishi kerak")

    if q_type == "practical":
        samples = item.get("sample_tests")
        hidden = item.get("hidden_tests")
        if not isinstance(samples, list) or len(samples) < 1:
            errors.append(f"{prefix}: practical uchun kamida 1 ta sample_tests kerak")
        if not isinstance(hidden, list) or len(hidden) < 1:
            errors.append(f"{prefix}: practical uchun kamida 1 ta hidden_tests kerak")
        for group_name, group in (("sample_tests", samples or []), ("hidden_tests", hidden or [])):
            for t_i, tc in enumerate(group):
                if not isinstance(tc, dict) or "input" not in tc or "expected" not in tc:
                    errors.append(f"{prefix}: {group_name}[{t_i}] da 'input' va 'expected' bo'lishi kerak")

    return errors


async def run_import(json_path: Path, challenge_id: str, dry_run: bool) -> int:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print("Xato: JSON ildizi ro'yxat (array) bo'lishi kerak.")
        return 1

    ch_uuid = uuid.UUID(challenge_id)
    async with async_session_maker() as db:
        days_res = await db.execute(
            select(ChallengeDay).where(ChallengeDay.challenge_id == ch_uuid)
        )
        days = days_res.scalars().all()
        day_map = {d.day_number: d for d in days}

        all_errors: list[str] = []
        for idx, item in enumerate(data):
            all_errors.extend(validate_question_item(item, idx, set(day_map.keys())))

        if all_errors:
            print("Tekshiruvda xatolar topildi:")
            for err in all_errors:
                print(f"  - {err}")
            return 1

        if dry_run:
            print(f"[DRY-RUN] {len(data)} ta savol barcha tekshiruvlardan o'tdi. Bazaga yozilmadi.")
            return 0

        for item in data:
            day = day_map[item["day_number"]]
            q = Question(
                challenge_day_id=day.id,
                title=item["title"],
                question_type=item["question_type"],
                body_text=item["body_text"],
                difficulty=item["difficulty"],
                starter_code=item.get("starter_code", ""),
                sample_tests=item.get("sample_tests"),
                hidden_tests=item.get("hidden_tests"),
                options=item.get("options"),
                correct_option=item.get("correct_option"),
                reference_solution=item.get("reference_solution"),
            )
            db.add(q)

        await db.commit()
        print(f"Muvaffaqiyatli: {len(data)} ta savol bazaga yuklandi.")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Import PyChallenge questions from JSON.")
    parser.add_argument("json_file", type=Path, help="Savollar JSON fayli")
    parser.add_argument("--challenge-id", required=True, help="Challenge UUID")
    parser.add_argument("--dry-run", action="store_true", help="Bazaga yozmasdan tekshirish")
    args = parser.parse_args()

    rc = asyncio.run(run_import(args.json_file, args.challenge_id, args.dry_run))
    sys.exit(rc)


if __name__ == "__main__":
    main()
