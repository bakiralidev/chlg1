import asyncio
import os
import time
from pathlib import Path

import httpx

RUNNER_URL = os.environ.get("RUNNER_URL", "http://runner:8080").rstrip("/")


def _load_secret() -> str:
    secret = os.environ.get("RUNNER_SHARED_SECRET", "")
    if secret:
        return secret
    for p in (Path("/app/.env"), Path(".env")):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.startswith("RUNNER_SHARED_SECRET="):
                    return line.split("=", 1)[1].strip()
    return ""


SECRET = _load_secret()


async def call_runner(client: httpx.AsyncClient, code: str, timeout_s: float = 5.0) -> dict:
    resp = await client.post(
        f"{RUNNER_URL}/run",
        headers={"X-Runner-Key": SECRET},
        json={"code": code, "stdin": "", "time_limit_s": timeout_s},
        timeout=timeout_s + 5.0,
    )
    resp.raise_for_status()
    return resp.json()


async def main() -> int:
    results: list[tuple[str, bool, str]] = []

    async with httpx.AsyncClient() as client:
        # 1. os.environ
        r = await call_runner(client, "import os; print(dict(os.environ))")
        leak = any(k in r["stdout"] for k in ("JWT", "POSTGRES", "TELEGRAM", "RUNNER_SHARED_SECRET"))
        results.append(("1. os.environ", (not leak and r["exit_code"] == 0), "sirlar yo'q" if not leak else "LEAK"))

        # 2. /proc/self/environ
        r = await call_runner(client, "print(open('/proc/self/environ').read())")
        leak = any(k in r["stdout"] for k in ("JWT", "POSTGRES", "TELEGRAM", "RUNNER_SHARED_SECRET"))
        results.append(("2. /proc/self/environ", (not leak and r["exit_code"] == 0), "sirlar yo'q" if not leak else "LEAK"))

        # 3. filesystem: /backend, /app
        r = await call_runner(
            client,
            "import os\n"
            "for p in ('/backend', '/app', '/app/main.py'):\n"
            "  try:\n"
            "    print(p, os.listdir(p) if os.path.isdir(p) else open(p).read(20))\n"
            "  except Exception as e:\n"
            "    print(p, type(e).__name__)\n",
        )
        ok = ("PermissionError" in r["stdout"] or "FileNotFoundError" in r["stdout"]) and "FastAPI" not in r["stdout"]
        results.append(("3. /backend va /app", ok, r["stdout"].strip().replace("\n", "; ")[:80]))

        # 4. socket: db, backend:8000, 127.0.0.1:8080, 8.8.8.8:53
        r = await call_runner(
            client,
            "import socket\n"
            "for host, port in [('postgres',5432),('backend',8000),('127.0.0.1',8080),('8.8.8.8',53)]:\n"
            "  try:\n"
            "    s = socket.socket(); s.settimeout(1); s.connect((host, port))\n"
            "    print(host, 'CONNECTED')\n"
            "  except Exception as e:\n"
            "    print(host, type(e).__name__, getattr(e, 'errno', ''))\n",
        )
        ok = "CONNECTED" not in r["stdout"] and "PermissionError" in r["stdout"]
        results.append(("4. soketlar (EPERM)", ok, r["stdout"].strip().replace("\n", "; ")[:80]))

        # 5. cheksiz sikl
        r = await call_runner(client, "while True: pass", timeout_s=2.0)
        results.append(("5. cheksiz sikl", r["timed_out"] is True, f"timed_out={r['timed_out']} ms={r['duration_ms']}"))

        # 6. fork bomb
        r = await call_runner(client, "import os\nfor _ in range(100):\n  os.fork()\n", timeout_s=2.0)
        alive = await call_runner(client, "print('ALIVE')")
        ok = r["exit_code"] != 0 and "ALIVE" in alive["stdout"]
        results.append(("6. fork bomb", ok, f"exit={r['exit_code']} runner_alive={'ALIVE' in alive['stdout']}"))

        # 7. memory bomb
        r = await call_runner(client, "x = 'a' * (10**10); print(len(x))", timeout_s=3.0)
        ok = r["exit_code"] != 0 and ("MemoryError" in r["stderr"] or r["exit_code"] != 0)
        results.append(("7. xotira to'ldirish", ok, f"exit={r['exit_code']}"))

        # 8. chunked large file
        r = await call_runner(
            client,
            "with open('big.bin','wb') as f:\n"
            "  for _ in range(20):\n"
            "    f.write(b'x'*(256*1024))\n",
            timeout_s=3.0,
        )
        ok = r["exit_code"] != 0 and ("File too large" in r["stderr"] or "OSError" in r["stderr"])
        results.append(("8. bo'lak-bo'lak katta fayl", ok, r["stderr"].splitlines()[-1][:80] if r["stderr"] else "no err"))

        # 9. output flood (< 2s, truncated=True)
        t0 = time.monotonic()
        r = await call_runner(client, "while True: print('x'*1000)", timeout_s=5.0)
        dt = time.monotonic() - t0
        ok = r["truncated"] is True and dt < 2.0
        results.append(("9. chiqish toshqini", ok, f"truncated={r['truncated']} time={dt:.2f}s"))

        # 10. os.system / subprocess curl & sh
        r = await call_runner(
            client,
            "import os, subprocess\n"
            "rc = os.system('curl -s https://example.com >/dev/null 2>&1')\n"
            "print('rc=', rc)\n",
            timeout_s=3.0,
        )
        ok = "rc= 0" not in r["stdout"]
        results.append(("10. os.system/curl", ok, r["stdout"].strip()[:60]))

        # 11. persistent file
        await call_runner(client, "open('/tmp/persist_test.txt','w').write('secret')")
        r = await call_runner(client, "print(open('/tmp/persist_test.txt').read())")
        ok = r["exit_code"] != 0
        results.append(("11. qoldiq fayl yo'q", ok, f"read_exit={r['exit_code']}"))

        # 12. parallel neighbor code reading (spy vs victim)
        victim_code = "import time\nsecret = 'VICTIM_' + 'SECRET_9911'\ntime.sleep(0.8)\nprint(len(secret))"
        spy_code = (
            "import glob, os, time\n"
            "target = 'VICTIM_' + 'SECRET'\n"
            "time.sleep(0.2)\n"
            "found = []\n"
            "for p in glob.glob('/tmp/run_*') + glob.glob('/tmp/run_*/**', recursive=True):\n"
            "  try:\n"
            "    if os.path.isfile(p) and target in open(p, errors='ignore').read(): found.append(p)\n"
            "  except Exception: pass\n"
            "for pid in os.listdir('/proc'):\n"
            "  if not pid.isdigit() or pid == str(os.getpid()): continue\n"
            "  for sub in ('cmdline', 'environ', 'cwd'):\n"
            "    try:\n"
            "      path = f'/proc/{pid}/{sub}'\n"
            "      data = os.readlink(path) if sub == 'cwd' else open(path, errors='ignore').read()\n"
            "      if target in data: found.append(path)\n"
            "    except Exception: pass\n"
            "print('FOUND:', found)\n"
        )
        rv, rs = await asyncio.gather(call_runner(client, victim_code), call_runner(client, spy_code))
        ok = "FOUND: []" in rs["stdout"] and rv["exit_code"] == 0
        results.append(("12. qo'shni kodini o'qish", ok, rs["stdout"].strip()[:80]))

        # 13. 20 parallel normal runs
        parallel_res = await asyncio.gather(
            *[call_runner(client, f"print({i}*{i})") for i in range(20)]
        )
        all_ok = all(
            res["exit_code"] == 0 and res["stdout"].strip() == str(i * i)
            for i, res in enumerate(parallel_res)
        )
        results.append(("13. 20 parallel oddiy kod", all_ok, f"passed={sum(1 for r in parallel_res if r['exit_code']==0)}/20"))

        # 14. auth: missing & wrong X-Runner-Key -> 401
        r_no_key = await client.post(f"{RUNNER_URL}/run", json={"code": "print(1)"})
        r_bad_key = await client.post(f"{RUNNER_URL}/run", headers={"X-Runner-Key": "wrong"}, json={"code": "print(1)"})
        ok = r_no_key.status_code == 401 and r_bad_key.status_code == 401
        results.append(("14. Runner auth (401)", ok, f"no_key={r_no_key.status_code} bad_key={r_bad_key.status_code}"))

        # 15. sandbox -> 127.0.0.1:8080 HTTP
        r = await call_runner(
            client,
            "import urllib.request\n"
            "try:\n"
            "  print(urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=1).read())\n"
            "except Exception as e:\n"
            "  print(type(e).__name__, e)\n",
        )
        ok = "ok" not in r["stdout"]
        results.append(("15. sandbox -> 127.0.0.1:8080", ok, r["stdout"].strip()[:80]))

        # 16. setuid(0), /proc/sys, mount
        r = await call_runner(
            client,
            "import os\n"
            "for fn in [lambda: os.setuid(0), lambda: open('/proc/sys/kernel/hostname','w').write('x')]:\n"
            "  try:\n"
            "    fn(); print('ALLOWED')\n"
            "  except Exception as e:\n"
            "    print(type(e).__name__)\n",
        )
        ok = "ALLOWED" not in r["stdout"] and "PermissionError" in r["stdout"]
        results.append(("16. setuid(0) va /proc/sys", ok, r["stdout"].strip().replace("\n", "; ")[:80]))

    print("\n=== SANDBOX ATTACK TEST NATIJALARI ===")
    passed = 0
    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"[{status}] {name:30s} | {detail}")
    print(f"\nJAMI: {passed}/{len(results)} PASS, {len(results) - passed} FAIL")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
