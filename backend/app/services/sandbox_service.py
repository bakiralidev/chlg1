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


async def execute_python_code(code: str, input_data: str = "", timeout_seconds: float = 5.0) -> dict[str, Any]:
    """
    Kodni Python subprocess orqali xavfsiz timeout bilan ishga tushiradi.
    stdout, stderr, exit_code va execution_ms qaytaradi.
    """
    import sys
    start_time = time.time()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    stdout_str = ""
    stderr_str = ""
    exit_code = 0

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable, tmp_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdin_bytes = (input_data or "").encode("utf-8")
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=stdin_bytes),
                timeout=timeout_seconds,
            )
            stdout_str = stdout_bytes.decode("utf-8", errors="replace")
            stderr_str = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = proc.returncode if proc.returncode is not None else 0
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            stdout_str = ""
            stderr_str = f"⏱️ Vaqt chegarasidan oshib ketdi (Timeout {timeout_seconds}s). Cheksiz tsikl (infinite loop) mavjud bo'lishi mumkin."
            exit_code = -1
    except Exception as e:
        stdout_str = ""
        stderr_str = f"Ishga tushirishda xato yuz berdi: {str(e)}"
        exit_code = -1
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    execution_ms = int((time.time() - start_time) * 1000)

    return {
        "stdout": stdout_str,
        "stderr": stderr_str,
        "exit_code": exit_code,
        "execution_ms": execution_ms,
    }
