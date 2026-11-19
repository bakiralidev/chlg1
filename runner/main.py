import asyncio
import hmac
import math
import os
import shutil
import signal
import sys
import tempfile
import time
from collections import deque

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

MAX_CODE_BYTES = 50 * 1024       # 50 KB
MAX_OUTPUT_BYTES = 64 * 1024     # 64 KB
MAX_CONCURRENT_RUNS = 8
MAX_QUEUE_WAITING = 16
BASE_SANDBOX_UID = 20000
RUNNER_SHARED_SECRET = os.environ.get("RUNNER_SHARED_SECRET", "")

app = FastAPI(title="PyChallenge Isolated Runner", docs_url=None, redoc_url=None)


class SlotPool:
    """Manages unique per-execution UID/GID slots so concurrent runs never share a UID."""

    def __init__(self, num_slots: int = MAX_CONCURRENT_RUNS, base_uid: int = BASE_SANDBOX_UID) -> None:
        self.num_slots = num_slots
        self.base_uid = base_uid
        self._semaphore = asyncio.Semaphore(num_slots)
        self._free_slots: deque[int] = deque(range(num_slots))
        self._active_and_waiting = 0
        self._lock = asyncio.Lock()

    async def try_enter_queue(self, max_total: int) -> bool:
        async with self._lock:
            if self._active_and_waiting >= max_total:
                return False
            self._active_and_waiting += 1
            return True

    async def leave_queue(self) -> None:
        async with self._lock:
            self._active_and_waiting = max(0, self._active_and_waiting - 1)

    async def acquire_slot(self) -> tuple[int, int, int]:
        await self._semaphore.acquire()
        async with self._lock:
            slot_idx = self._free_slots.popleft()
        uid = self.base_uid + slot_idx
        return slot_idx, uid, uid

    async def release_slot(self, slot_idx: int) -> None:
        async with self._lock:
            self._free_slots.append(slot_idx)
        self._semaphore.release()


_slot_pool = SlotPool()


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


def verify_runner_key(x_runner_key: str | None = Header(default=None, alias="X-Runner-Key")) -> None:
    if not RUNNER_SHARED_SECRET or not x_runner_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not hmac.compare_digest(x_runner_key, RUNNER_SHARED_SECRET):
        raise HTTPException(status_code=401, detail="Unauthorized")


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


def _sandbox_child_preexec(slot_uid: int, slot_gid: int, time_limit_s: float) -> None:
    from seccomp_filter import drop_bounding_caps_and_no_new_privs, install_sandbox_seccomp

    os.setgroups([])
    os.setgid(slot_gid)
    os.setuid(slot_uid)
    drop_bounding_caps_and_no_new_privs()
    _apply_posix_limits(time_limit_s)
    install_sandbox_seccomp()


def _kill_process_group(proc) -> None:
    if proc is None or proc.pid is None:
        return
    try:
        if os.name != "nt":
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        else:
            proc.kill()
    except Exception:
        pass


async def _read_stream_capped(
    stream: asyncio.StreamReader | None,
    target: bytearray,
    state: dict,
    proc,
    max_bytes: int = MAX_OUTPUT_BYTES,
) -> None:
    if stream is None:
        return
    while True:
        chunk = await stream.read(4096)
        if not chunk:
            break
        remaining = max_bytes - state["total"]
        if remaining <= 0:
            state["truncated"] = True
            _kill_process_group(proc)
            break
        if len(chunk) > remaining:
            target.extend(chunk[:remaining])
            state["total"] += remaining
            state["truncated"] = True
            _kill_process_group(proc)
            break
        target.extend(chunk)
        state["total"] += len(chunk)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/run", response_model=RunResponse, dependencies=[Depends(verify_runner_key)])
async def run_code(req: RunRequest):
    code_bytes = req.code.encode("utf-8")
    if len(code_bytes) > MAX_CODE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Kod hajmi {MAX_CODE_BYTES // 1024} KB dan oshmasligi kerak",
        )

    entered = await _slot_pool.try_enter_queue(MAX_CONCURRENT_RUNS + MAX_QUEUE_WAITING)
    if not entered:
        raise HTTPException(status_code=503, detail="Tizim band, birozdan keyin qayta urining")

    try:
        slot_idx, slot_uid, slot_gid = await _slot_pool.acquire_slot()
        try:
            return await _execute_isolated(code_bytes, req.stdin or "", req.time_limit_s, slot_uid, slot_gid)
        finally:
            await _slot_pool.release_slot(slot_idx)
    finally:
        await _slot_pool.leave_queue()


async def _execute_isolated(
    code_bytes: bytes,
    stdin_text: str,
    time_limit_s: float,
    slot_uid: int,
    slot_gid: int,
) -> RunResponse:
    tmpdir = tempfile.mkdtemp(prefix="run_", dir="/tmp" if os.name != "nt" else None)
    if os.name != "nt":
        os.chmod(tmpdir, 0o700)
        os.chown(tmpdir, slot_uid, slot_gid)

    clean_env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HOME": tmpdir,
        "TMPDIR": tmpdir,
        "LANG": "C.UTF-8",
    }

    r_fd, w_fd = os.pipe()
    # Pass user code via inherited pipe FD (not on disk, not in /proc/pid/cmdline)
    bootstrap = (
        f"import os; _c=os.fdopen({r_fd},'rb').read().decode('utf-8'); "
        "exec(compile(_c,'solution.py','exec'),{'__name__':'__main__'})"
    )

    start_time = time.monotonic()
    timed_out = False
    stdout_buf = bytearray()
    stderr_buf = bytearray()
    stream_state = {"total": 0, "truncated": False}
    exit_code = 0

    popen_kwargs: dict = {
        "stdin": asyncio.subprocess.PIPE,
        "stdout": asyncio.subprocess.PIPE,
        "stderr": asyncio.subprocess.PIPE,
        "cwd": tmpdir,
        "env": clean_env,
        "pass_fds": (r_fd,),
    }
    if os.name != "nt":
        popen_kwargs["start_new_session"] = True
        popen_kwargs["preexec_fn"] = lambda: _sandbox_child_preexec(slot_uid, slot_gid, time_limit_s)

    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-I",
            "-c",
            bootstrap,
            **popen_kwargs,
        )
        os.close(r_fd)
        r_fd = -1

        # Write code to pipe FD and close write end
        view = memoryview(code_bytes)
        written = 0
        while written < len(view):
            written += os.write(w_fd, view[written:])
        os.close(w_fd)
        w_fd = -1

        # Feed stdin and close stdin
        if proc.stdin is not None:
            if stdin_text:
                proc.stdin.write(stdin_text.encode("utf-8"))
                await proc.stdin.drain()
            proc.stdin.close()

        async def _collect():
            await asyncio.gather(
                _read_stream_capped(proc.stdout, stdout_buf, stream_state, proc),
                _read_stream_capped(proc.stderr, stderr_buf, stream_state, proc),
                proc.wait(),
            )

        try:
            await asyncio.wait_for(_collect(), timeout=time_limit_s)
            exit_code = proc.returncode if proc.returncode is not None else 0
        except asyncio.TimeoutError:
            timed_out = True
            exit_code = -1
            _kill_process_group(proc)
            try:
                await asyncio.wait_for(proc.wait(), timeout=1.0)
            except Exception:
                pass
            stderr_buf = bytearray(f"Vaqt chegarasidan oshib ketdi (Timeout {time_limit_s}s).".encode("utf-8"))
    finally:
        if r_fd >= 0:
            try:
                os.close(r_fd)
            except OSError:
                pass
        if w_fd >= 0:
            try:
                os.close(w_fd)
            except OSError:
                pass
        shutil.rmtree(tmpdir, ignore_errors=True)

    duration_ms = int((time.monotonic() - start_time) * 1000)
    stdout_str = bytes(stdout_buf).decode("utf-8", errors="replace")
    stderr_str = bytes(stderr_buf).decode("utf-8", errors="replace")
    if stream_state["truncated"]:
        exit_code = -1
        if stderr_str and not stderr_str.endswith("\n"):
            stderr_str += "\n"
        stderr_str += "Chiqish hajmi chegarasidan oshdi (64 KB)."

    return RunResponse(
        stdout=stdout_str,
        stderr=stderr_str,
        exit_code=exit_code,
        timed_out=timed_out,
        duration_ms=duration_ms,
        truncated=stream_state["truncated"],
    )
