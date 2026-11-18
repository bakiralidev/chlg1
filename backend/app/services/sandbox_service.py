import json
import time
from typing import Any

import httpx

from app.core.config import settings

MAX_CODE_BYTES = 50 * 1024


class RunnerUnavailableError(Exception):
    """Raised when the isolated runner service is unreachable or overloaded."""


async def execute_python_code(
    code: str,
    input_data: str = "",
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    """Send Python code to the isolated runner service for execution."""
    if len((code or "").encode("utf-8")) > MAX_CODE_BYTES:
        return {
            "stdout": "",
            "stderr": "Kod hajmi 50 KB dan oshmasligi kerak.",
            "exit_code": -1,
            "timed_out": False,
            "execution_ms": 0,
            "truncated": False,
        }

    limit = timeout_seconds if timeout_seconds is not None else settings.RUNNER_TIMEOUT_SECS
    url = f"{settings.RUNNER_URL.rstrip('/')}/run"

    try:
        async with httpx.AsyncClient(timeout=limit + 3.0) as client:
            resp = await client.post(
                url,
                json={"code": code, "stdin": input_data or "", "time_limit_s": limit},
            )
    except httpx.HTTPError:
        raise RunnerUnavailableError("Kod bajarish xizmati vaqtincha mavjud emas.")

    if resp.status_code == 503:
        raise RunnerUnavailableError("Tizim band, birozdan keyin qayta urining.")
    if resp.status_code == 400:
        detail = resp.json().get("detail", "Kod noto'g'ri")
        return {
            "stdout": "",
            "stderr": detail,
            "exit_code": -1,
            "timed_out": False,
            "execution_ms": 0,
            "truncated": False,
        }
    resp.raise_for_status()
    data = resp.json()
    return {
        "stdout": data.get("stdout", ""),
        "stderr": data.get("stderr", ""),
        "exit_code": data.get("exit_code", 0),
        "timed_out": bool(data.get("timed_out", False)),
        "execution_ms": int(data.get("duration_ms", 0)),
        "truncated": bool(data.get("truncated", False)),
    }


async def run_code_in_sandbox(
    code: str,
    test_cases: list[dict[str, Any]],
    *,
    timeout_per_test: float | None = None,
) -> dict[str, Any]:
    """
    Run user code against a list of test cases in the isolated runner.
    Returns aggregated pass/fail/error/timeout result without leaking expected outputs.
    """
    if not test_cases:
        return {
            "status": "error",
            "passed": 0,
            "total": 0,
            "execution_ms": 0,
            "results": [],
            "output": "[]",
        }

    passed = 0
    total = len(test_cases)
    results: list[dict[str, Any]] = []
    start_time = time.monotonic()

    for idx, tc in enumerate(test_cases, start=1):
        stdin_val = str(tc.get("input", ""))
        expected = str(tc.get("expected", "")).strip()
        try:
            res = await execute_python_code(
                code=code,
                input_data=stdin_val,
                timeout_seconds=timeout_per_test,
            )
        except RunnerUnavailableError as err:
            results.append({"test": idx, "status": "error", "error": str(err)})
            continue

        actual = (res.get("stdout") or "").strip()
        if res.get("timed_out"):
            results.append({"test": idx, "status": "timeout"})
        elif res.get("exit_code", 0) != 0:
            err_msg = (res.get("stderr") or "").strip()[:300]
            results.append({"test": idx, "status": "error", "error": err_msg or "Runtime xatolik"})
        elif actual == expected:
            passed += 1
            results.append({"test": idx, "status": "pass"})
        else:
            results.append({"test": idx, "status": "fail"})

    execution_ms = int((time.monotonic() - start_time) * 1000)

    if passed == total:
        status = "pass"
    elif any(r["status"] == "timeout" for r in results):
        status = "timeout"
    elif any(r["status"] == "error" for r in results) and passed == 0:
        status = "error"
    else:
        status = "fail"

    return {
        "status": status,
        "passed": passed,
        "total": total,
        "execution_ms": execution_ms,
        "results": results,
        "output": json.dumps(results, ensure_ascii=False),
    }
