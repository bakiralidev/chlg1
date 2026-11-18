import asyncio
import math
import os
import shutil
import signal
import sys
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

MAX_CODE_BYTES = 50 * 1024       # 50 KB
MAX_OUTPUT_BYTES = 64 * 1024     # 64 KB
MAX_CONCURRENT_RUNS = 4
MAX_QUEUE_WAITING = 8

app = FastAPI(title="PyChallenge Isolated Runner", docs_url=None, redoc_url=None)

_semaphore = asyncio.Semaphore(MAX_CONCURRENT_RUNS)
_active_and_waiting = 0
_counter_lock = asyncio.Lock()


class RunRequest(BaseModel):
    code: str = Field(..., min_length=0)
    stdin: str = ""
    time_limit_s: float = Field(default=5.0, ge=0.5, le=10.0)


class RunResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    duration_ms: int
    truncated: bool


def _apply_posix_limits(time_limit_s: float) -> None:
    try:
        import resource
    except ImportError:
        return

    cpu_limit = max(1, int(math.ceil(time_limit_s)) + 1)
    mem_bytes = 128 * 1024 * 1024      # 128 MB address space
    fsize_bytes = 1 * 1024 * 1024      # 1 MB max created file
    nofile_limit = 32
    nproc_limit = 16

    resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit))
    resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    resource.setrlimit(resource.RLIMIT_FSIZE, (fsize_bytes, fsize_bytes))
    resource.setrlimit(resource.RLIMIT_NOFILE, (nofile_limit, nofile_limit))
    if hasattr(resource, "RLIMIT_NPROC"):
        resource.setrlimit(resource.RLIMIT_NPROC, (nproc_limit, nproc_limit))


def _truncate_bytes(data: bytes, limit: int = MAX_OUTPUT_BYTES) -> tuple[str, bool]:
    if len(data) > limit:
        return data[:limit].decode("utf-8", errors="replace") + "\n...[chiqish 64 KB dan oshgani uchun kesildi]", True
    return data.decode("utf-8", errors="replace"), False


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/run", response_model=RunResponse)
async def run_code(req: RunRequest):
    global _active_and_waiting

    code_bytes = req.code.encode("utf-8")
    if len(code_bytes) > MAX_CODE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Kod hajmi {MAX_CODE_BYTES // 1024} KB dan oshmasligi kerak",
        )

    async with _counter_lock:
        if _active_and_waiting >= MAX_CONCURRENT_RUNS + MAX_QUEUE_WAITING:
            raise HTTPException(status_code=503, detail="Tizim band, birozdan keyin qayta urining")
        _active_and_waiting += 1

    try:
        async with _semaphore:
            return await _execute_isolated(req.code, req.stdin or "", req.time_limit_s)
    finally:
        async with _counter_lock:
            _active_and_waiting -= 1


async def _execute_isolated(code: str, stdin_text: str, time_limit_s: float) -> RunResponse:
    tmpdir = tempfile.mkdtemp(prefix="run_", dir="/tmp" if os.name != "nt" else None)
    script_path = Path(tmpdir) / "solution.py"
    script_path.write_text(code, encoding="utf-8")

    clean_env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": tmpdir,
        "TMPDIR": tmpdir,
    }

    start_time = time.monotonic()
    timed_out = False
    stdout_bytes = b""
    stderr_bytes = b""
    exit_code = 0

    popen_kwargs: dict = {
        "stdin": asyncio.subprocess.PIPE,
        "stdout": asyncio.subprocess.PIPE,
        "stderr": asyncio.subprocess.PIPE,
        "cwd": tmpdir,
        "env": clean_env,
    }
    if os.name != "nt":
        popen_kwargs["start_new_session"] = True
        popen_kwargs["preexec_fn"] = lambda: _apply_posix_limits(time_limit_s)

    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            str(script_path),
            **popen_kwargs,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=stdin_text.encode("utf-8")),
                timeout=time_limit_s,
            )
            exit_code = proc.returncode if proc.returncode is not None else 0
        except asyncio.TimeoutError:
            timed_out = True
            exit_code = -1
            if proc.pid is not None:
                try:
                    if os.name != "nt":
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    else:
                        proc.kill()
                except Exception:
                    pass
            try:
                await asyncio.wait_for(proc.wait(), timeout=1.0)
            except Exception:
                pass
            stderr_bytes = f"Vaqt chegarasidan oshib ketdi (Timeout {time_limit_s}s).".encode("utf-8")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    duration_ms = int((time.monotonic() - start_time) * 1000)
    stdout_str, trunc_out = _truncate_bytes(stdout_bytes)
    stderr_str, trunc_err = _truncate_bytes(stderr_bytes)

    return RunResponse(
        stdout=stdout_str,
        stderr=stderr_str,
        exit_code=exit_code,
        timed_out=timed_out,
        duration_ms=duration_ms,
        truncated=trunc_out or trunc_err,
    )
