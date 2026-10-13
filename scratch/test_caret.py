import win32gui
import win32process
import ctypes
from ctypes import wintypes

class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('flags', wintypes.DWORD),
        ('hwndActive', wintypes.HWND),
        ('hwndFocus', wintypes.HWND),
        ('hwndCapture', wintypes.HWND),
        ('hwndMenuOwner', wintypes.HWND),
        ('hwndMoveSize', wintypes.HWND),
        ('hwndCaret', wintypes.HWND),
        ('rcCaret', wintypes.RECT)
    ]

def get_active_caret_screen_rect():
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return None
    tid, pid = win32process.GetWindowThreadProcessId(hwnd)
    info = GUITHREADINFO()
    info.cbSize = ctypes.sizeof(GUITHREADINFO)
    if ctypes.windll.user32.GetGUIThreadInfo(tid, ctypes.byref(info)):
        # If caret or focused control exists, convert coordinates to screen space
        target_hwnd = info.hwndCaret or info.hwndFocus or hwnd
        if target_hwnd:
            pt = wintypes.POINT(info.rcCaret.left, info.rcCaret.top)
            ctypes.windll.user32.ClientToScreen(target_hwnd, ctypes.byref(pt))
            w = max(180, info.rcCaret.right - info.rcCaret.left + 80)
            h = max(36, info.rcCaret.bottom - info.rcCaret.top + 20)
            rect = win32gui.GetWindowRect(target_hwnd)
            return {
                "x": pt.x,
                "y": pt.y,
                "width": w,
                "height": h,
                "window_rect": rect,
                "title": win32gui.GetWindowText(hwnd)
            }
    # Fallback to focused window rect
    rect = win32gui.GetWindowRect(hwnd)
    return {
        "x": rect[0] + 50,
        "y": rect[1] + 50,
        "width": rect[2] - rect[0] - 100,
        "height": rect[3] - rect[1] - 100,
        "window_rect": rect,
        "title": win32gui.GetWindowText(hwnd)
    }

if __name__ == "__main__":
    res = get_active_caret_screen_rect()
    print("Detected caret/window rect:", res)
