import json, threading, urllib.request

URL = "http://runner:8080/run"

def run(code, t=8):
    body = json.dumps({"code": code, "stdin": "", "time_limit_s": t}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())

def show(name, r):
    print(f"\n=== {name}")
    print("exit:", r.get("exit_code"), "| timeout:", r.get("timed_out"),
          "| truncated:", r.get("truncated"), "| ms:", r.get("duration_ms"))
    print("stdout:", (r.get("stdout") or "")[:400].replace("\n", " | "))
    print("stderr:", (r.get("stderr") or "")[:300].replace("\n", " | "))

# A) backend va runner'ning o'ziga yetib borish
show("A  backend/runner'ga HTTP", run("""
import urllib.request
for u in ['http://backend:8000/docs', 'http://backend:8000/api/v1/auth/login', 'http://127.0.0.1:8080/docs']:
    try:
        r = urllib.request.urlopen(u, timeout=3); print('YETDI', u, r.status)
    except Exception as e:
        print(type(e).__name__, u, str(e)[:50])
"""))

# B) bir vaqtda ishlaganda qo'shni kodini o'qish
res = {}
victim = "# VICTIM_SECRET_12345\nimport time\ntime.sleep(4)\nprint('victim tugadi')"
spy = """
import glob, os, time
time.sleep(1.5)
out = []
for p in glob.glob('/tmp/run_*/solution.py'):
    try:
        out.append(('OQILDI' if 'VICTIM_SECRET' in open(p).read() else 'oqildi-boshqa', p))
    except Exception as e:
        out.append(('rad', p, type(e).__name__))
for pid in os.listdir('/proc'):
    if pid.isdigit():
        try: out.append(('proc', pid, os.readlink('/proc/%s/cwd' % pid)))
        except Exception: pass
print(out)
"""
def t_victim(): res['v'] = run(victim)
def t_spy(): res['s'] = run(spy)
th = [threading.Thread(target=t_victim), threading.Thread(target=t_spy)]
[x.start() for x in th]; [x.join() for x in th]
show("B  qo'shni kodini o'qish (spy)", res['s'])

# C) fayl hajmi limiti (bo'lak-bo'lak yozish)
show("C  katta fayl, bo'lak-bo'lak", run("""
f = open('/tmp/big', 'wb')
for i in range(300):
    f.write(b'a' * 1024 * 1024)
f.flush()
print('YOZILDI 300 MB')
"""))

# D) ko'p chiqish (keyin runner o'lmaganini tekshiring)
show("D  chiqish toshqini", run("""
import sys
while True:
    sys.stdout.write('x' * 1000 + '\\n')
""", t=5))

# E) parallel oddiy yuklama: 10 ta bir vaqtda
results = []
def legit(i):
    try:
        r = run("print(sum(k*k for k in range(10**6)))", t=8)
        results.append((i, r['exit_code'], (r['stderr'] or '')[:60]))
    except Exception as e:
        results.append((i, 'XATO', str(e)[:60]))
ths = [threading.Thread(target=legit, args=(i,)) for i in range(10)]
[x.start() for x in ths]; [x.join() for x in ths]
ok = sum(1 for r in results if r[1] == 0)
print(f"\n=== E  10 ta parallel oddiy kod: {ok}/10 muvaffaqiyatli")
for r in results:
    if r[1] != 0: print("   muammo:", r)