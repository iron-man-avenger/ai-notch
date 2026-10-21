import ctypes
from ctypes import wintypes
import psutil

EnumWindows = ctypes.windll.user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
GetWindowText = ctypes.windll.user32.GetWindowTextW
GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
IsWindowVisible = ctypes.windll.user32.IsWindowVisible

windows = []
def callback(hwnd, extra):
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
    return True

EnumWindows(EnumWindowsProc(callback), 0)
for pid, pname, title in windows:
    if any(k in title.lower() or k in pname.lower() for k in ["teams", "assistant", "dock", "chrome", "code", "ai"]):
        print(f"[{pname} | PID {pid}]: {title}")
