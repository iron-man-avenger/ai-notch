import win32gui
import win32process
import psutil

def enum_cb(hwnd, results):
    if win32gui.IsWindowVisible(hwnd):
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            p = psutil.Process(pid)
            pname = p.name()
            if "teams" in pname.lower():
                title = win32gui.GetWindowText(hwnd)
                cls = win32gui.GetClassName(hwnd)
                rect = win32gui.GetWindowRect(hwnd)
                results.append((hwnd, pid, pname, title, cls, rect))
        except Exception:
            pass
    return True

res = []
win32gui.EnumWindows(enum_cb, res)
print(f"Total Teams windows found: {len(res)}")
for hwnd, pid, pname, title, cls, rect in res:
    print(f"HWND: {hwnd} | PID: {pid} | Process: {pname} | Class: {cls} | Rect: {rect} | Title: '{title}'")
