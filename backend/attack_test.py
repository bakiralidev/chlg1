import json, urllib.request

URL = "http://runner:8080/run"

TESTS = [
 ("1  env o'qish", "import os\nprint(dict(os.environ))"),
 ("2  /proc/self/environ", "print(open('/proc/self/environ').read())"),
 ("2b fayl tizimi", "import os\nprint(os.listdir('/'))\nprint(os.path.exists('/backend'), os.path.exists('/app'))"),
 ("3  tarmoq", "import socket\nfor h in [('db',5432),('backend',8000),('8.8.8.8',53)]:\n    try:\n        s=socket.socket(); s.settimeout(3); s.connect(h); print('ULANDI',h)\n    except Exception as e:\n        print('yopiq',h,type(e).__name__)"),
 ("4  cheksiz sikl", "while True: pass"),
 ("5  fork bomb", "import os\nwhile True:\n    os.fork()"),
 ("6  xotira", "x='a'*(10**10)\nprint(len(x))"),
 ("7  katta fayl", "open('/tmp/big','w').write('a'*(10**9))\nprint('yozildi')"),
 ("8  katta stdout", "for i in range(10**7): print('x'*100)"),
 ("9  shell/curl", "import os\nprint(os.system('curl -s -m 3 http://example.com | head -c 80; id'))"),
 ("10a fayl qoldirish", "open('/tmp/leftover.txt','w').write('secret')\nprint('yozildi')"),
 ("10b qoldiq bormi", "import glob\nprint(glob.glob('/tmp/**', recursive=True))"),
 ("11 oddiy kod (runner tirikmi)", "print(sum(range(10)))"),
]

for name, code in TESTS:
    body = json.dumps({"code": code, "stdin": "", "time_limit_s": 5}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=30).read())
        print(f"\n=== {name}")
        print("exit:", r.get("exit_code"), "| timeout:", r.get("timed_out"),
              "| truncated:", r.get("truncated"), "| ms:", r.get("duration_ms"))
        print("stdout:", (r.get("stdout") or "")[:200].replace("\n", " | "))
        print("stderr:", (r.get("stderr") or "")[:200].replace("\n", " | "))
    except Exception as e:
        print(f"\n=== {name}\nSO'ROV XATOSI:", type(e).__name__, e)