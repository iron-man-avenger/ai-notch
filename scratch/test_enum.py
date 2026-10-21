import ctypes
from ctypes import wintypes
import psutil

EnumWindows = ctypes.windll.user32.EnumWindows
WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HWND, wintypes.LPARAM)
GetWindowText = ctypes.windll.user32.GetWindowTextW
GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
IsWindowVisible = ctypes.windll.user32.IsWindowVisible

windows = []
def enum_proc(hwnd, lparam):
    if IsWindowVisible(hwnd):
        length = GetWindowTextLength(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            GetWindowText(hwnd, buff, length + 1)
            pid = wintypes.DWORD()
            GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            pname = "unknown"
            try:
                pname = psutil.Process(pid.value).name()
            except Exception:
                pass
            windows.append((pid.value, pname, buff.value))
    return 1

EnumWindows(WNDENUMPROC(enum_proc), 0)
print(f"Total visible windows with title: {len(windows)}")
for pid, pname, title in windows[:30]:
    print(f"[{pname} | PID {pid}]: {title}")
