import ctypes
from ctypes import wintypes
import psutil

EnumWindows = ctypes.windll.user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
GetWindowText = ctypes.windll.user32.GetWindowTextW
GetWindowTextLength = ctypes.windll.user32.GetWindowTextLengthW
IsWindowVisible = ctypes.windll.user32.IsWindowVisible
GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
GetClassName = ctypes.windll.user32.GetClassNameW

teams_hwnds = []

def callback(hwnd, extra):
    if IsWindowVisible(hwnd):
        pid = wintypes.DWORD()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        try:
            p = psutil.Process(pid.value)
            if "teams" in p.name().lower():
                length = GetWindowTextLength(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                GetWindowText(hwnd, buff, length + 1)
                
                cls_buff = ctypes.create_unicode_buffer(256)
                GetClassName(hwnd, cls_buff, 256)
                
                rect = wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                
                teams_hwnds.append({
                    "hwnd": hwnd,
                    "pid": pid.value,
                    "pname": p.name(),
                    "title": buff.value,
                    "class": cls_buff.value,
                    "w": rect.right - rect.left,
                    "h": rect.bottom - rect.top
                })
        except Exception:
            pass
    return True

EnumWindows(EnumWindowsProc(callback), 0)

print(f"Total visible Teams windows: {len(teams_hwnds)}")
for item in teams_hwnds:
    print(f"HWND {item['hwnd']} | PID {item['pid']} | {item['pname']} | Class: {item['class']} | Size: {item['w']}x{item['h']} | Title: '{item['title']}'")
