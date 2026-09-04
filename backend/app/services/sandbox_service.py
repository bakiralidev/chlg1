import asyncio
import os
import json
import tempfile
import time
from typing import Any


async def run_code_in_sandbox(code: str, test_cases: list[dict]) -> dict[str, Any]:
    """
    Docker sandbox ichida Python kodni ishga tushiradi va test keyslarni baholaydi.
    --network none, --memory=128m, --cpus=0.5, --pids-limit=50, 5s timeout
    """
    passed = 0
    total = len(test_cases)
    outputs = []
    start_time = time.time()

    # Har bir test keys uchun kodni ishga tushirish
    for i, tc in enumerate(test_cases):
        input_data = tc.get("input", "")
        expected = str(tc.get("expected", "")).strip()

        # Foydalanuvchi kodini + test wrapper ni birga yozish
        wrapper = f"""{code}

# Test runner
import sys
_input_data = {repr(input_data)}
_lines = iter(_input_data.split('\\n'))
import builtins
_orig_input = builtins.input
builtins.input = lambda *args, **kwargs: next(_lines, '')
"""
        # Vaqtinchalik fayl yaratish
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(wrapper)
            tmp_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "run", "--rm",
                "--network", "none",
                "--memory=128m",
                "--cpus=0.5",
                "--pids-limit=50",
                "--read-only",
                "-i",
                f"--volume={tmp_path}:/app/solution.py:ro",
                "python:3.11-alpine",
                "python", "/app/solution.py",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
                actual = stdout.decode("utf-8", errors="replace").strip()
                error_out = stderr.decode("utf-8", errors="replace").strip()

                if actual == expected:
                    passed += 1
                    outputs.append({"test": i + 1, "status": "pass", "output": actual})
                else:
                    outputs.append({
                        "test": i + 1,
                        "status": "fail",
                        "output": actual,
                        "expected": expected,
                        "error": error_out[:300] if error_out else None
                    })
            except asyncio.TimeoutError:
                proc.kill()
                outputs.append({"test": i + 1, "status": "timeout", "output": ""})
        except Exception as e:
            outputs.append({"test": i + 1, "status": "error", "output": str(e)[:200]})
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    execution_ms = int((time.time() - start_time) * 1000)

    # Umumiy status
    if passed == total:
        status = "pass"
    elif any(o["status"] == "timeout" for o in outputs):
        status = "timeout"
    elif any(o["status"] == "error" for o in outputs):
        status = "error"
    else:
        status = "fail"

    return {
        "status": status,
        "passed": passed,
        "total": total,
        "execution_ms": execution_ms,
        "output": json.dumps(outputs, ensure_ascii=False),
    }
