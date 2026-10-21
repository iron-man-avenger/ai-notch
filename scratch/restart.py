import psutil
import time
import os

count = 0
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        cmdline = p.info.get('cmdline') or []
        if any('main.py' in str(arg) for arg in cmdline) and p.pid != os.getpid():
            print(f"Terminating PID {p.pid}: {cmdline}")
            p.terminate()
            count += 1
    except Exception:
        pass

if count > 0:
    time.sleep(1.5)
    print(f"Terminated {count} main.py process(es).")
else:
    print("No main.py processes found running.")
