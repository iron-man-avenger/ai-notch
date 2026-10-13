import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import time
import threading
import urllib.request
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import math
import uvicorn
import win32con
import win32gui
from PySide6.QtCore import Qt, QUrl, QPoint, QRectF, QObject, Signal, Slot, QTimer
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QLinearGradient, QRadialGradient
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage

class WindowController(QObject):
    sig_resize = Signal(int, int)
    sig_move = Signal(int, int)
    sig_snap_top = Signal()
    sig_quit = Signal()
    sig_copy_clipboard = Signal(str)
    sig_hotkey_vision = Signal()
    sig_hotkey_voice = Signal()

    def __init__(self, window=None):
        super().__init__()
        self.window = window
        self.user_custom_moved = False
        self.sig_resize.connect(self._do_resize)
        self.sig_move.connect(self._do_move)
        self.sig_snap_top.connect(self._do_snap_top)
        self.sig_quit.connect(self._do_quit)
        self.sig_copy_clipboard.connect(self._do_copy_clipboard)
        self.sig_hotkey_vision.connect(self._do_hotkey_vision)
        self.sig_hotkey_voice.connect(self._do_hotkey_voice)

    @Slot()
    def _do_hotkey_vision(self):
        def _run_vision():
            try:
                import requests
                requests.post("http://127.0.0.1:8765/api/vision/analyze", json={"query": "Inspect screen", "focus": "general"}, timeout=12.0)
            except Exception as e:
                print("[Hotkey Vision Trigger Warning]", e)
        threading.Thread(target=_run_vision, daemon=True).start()

    @Slot()
    def _do_hotkey_voice(self):
        try:
            from server import broadcast_sync
            broadcast_sync({"type": "TRIGGER_VOICE_TOGGLE", "data": {}})
        except Exception as e:
            print("[Hotkey Voice Trigger Warning]", e)

    def capture_screen_sync(self, quality: int = 75) -> bytes:
        try:
            screen = QApplication.primaryScreen()
            if screen:
                pix = screen.grabWindow(0)
                from PySide6.QtCore import QBuffer, QIODevice
                buf = QBuffer()
                buf.open(QIODevice.OpenModeFlag.WriteOnly)
                pix.save(buf, "JPEG", quality)
                return bytes(buf.data().data())
        except Exception as e:
            print("[Capture Screen Sync Warning]", e)
        return b""

    @Slot()
    def _do_quit(self):
        QApplication.quit()

    @Slot(str)
    def _do_copy_clipboard(self, text: str):
        try:
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(text)
        except Exception as e:
            print("[WindowController Clipboard Warning]", e)

    def set_window(self, window):
        self.window = window

    @Slot(int, int)
    def _do_resize(self, width: int, height: int):
        if not self.window:
            return
        screen = QApplication.primaryScreen().geometry()
        if not self.user_custom_moved:
            x = (screen.width() - width) // 2
            y = 0
            self.window.setGeometry(x, y, width, height)
        else:
            cur_x = max(0, min(self.window.x(), screen.width() - width))
            cur_y = max(0, min(self.window.y(), screen.height() - height))
            self.window.setGeometry(cur_x, cur_y, width, height)

    @Slot(int, int)
    def _do_move(self, dx: int, dy: int):
        if not self.window:
            return
        screen = QApplication.primaryScreen().geometry()
        new_x = self.window.x() + dx
        new_y = self.window.y() + dy

        # If dragged within 15px of top screen edge, snap flush to top
        if new_y <= 15:
            new_y = 0
            # If also close to horizontal center, re-enable auto-center
            center_x = (screen.width() - self.window.width()) // 2
            if abs(new_x - center_x) < 40:
                new_x = center_x
                self.user_custom_moved = False
            else:
                self.user_custom_moved = True
        else:
            self.user_custom_moved = True

        # Clamp within screen bounds
        new_x = max(-self.window.width() // 2, min(new_x, screen.width() - self.window.width() // 2))
        new_y = max(0, min(new_y, screen.height() - 34))

        self.window.move(new_x, new_y)

    @Slot()
    def _do_snap_top(self):
        if not self.window:
            return
        self.user_custom_moved = False
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.window.width()) // 2
        self.window.setGeometry(x, 0, self.window.width(), self.window.height())

def start_backend(controller):
    if sys.platform == "win32":
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    from server import app, set_window_controller
    set_window_controller(controller)
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")

def wait_for_server(url="http://127.0.0.1:8765/api/status", timeout=12.0):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.1)
    return False

class NativeFloatingDock(QMainWindow):
    def __init__(self):
        super().__init__()

        # Native Windows Desktop Dock flags:
        # 1. FramelessWindowHint: No window borders, titlebars, or browser chrome
        # 2. WindowStaysOnTopHint: Always floats on top of VS Code, Teams, Chrome, etc.
        # 3. Tool: Prevents cluttering the taskbar
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        # True transparent glass background on Windows
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Qt WebEngine View to render the React Tailwind dock UI
        self.web_view = QWebEngineView(self)
        self.web_view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        
        # Auto-retry reload if connection refused
        self.web_view.loadFinished.connect(self._on_load_finished)
        self.web_view.page().featurePermissionRequested.connect(self._on_feature_permission)
        self.setCentralWidget(self.web_view)

        # Coucou-style Dynamic Island: Anchored to top-center edge (y = 0)
        # Initial compact notch is only 260px wide and 36px tall!
        # ZERO blocking of screen space below!
        screen = QApplication.primaryScreen().geometry()
        window_width = 680
        window_height = 36
        x = (screen.width() - window_width) // 2
        y = 0
        self.setGeometry(x, y, window_width, window_height)

    def _on_feature_permission(self, security_origin, feature):
        self.web_view.page().setFeaturePermission(
            security_origin, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
        )

    def _on_load_finished(self, ok: bool):
        if not ok:
            # Retry after 300ms if server was still initializing
            QTimer.singleShot(300, lambda: self.web_view.load(QUrl("http://127.0.0.1:8765")))

def start_global_hotkeys(controller: WindowController):
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        
        MOD_CTRL = 0x0002
        MOD_SHIFT = 0x0004
        MOD_NOREPEAT = 0x4000
        VK_S = 0x53
        VK_SPACE = 0x20
        
        HOTKEY_ID_VISION = 101
        HOTKEY_ID_VOICE = 102
        
        # Register Ctrl+Shift+S for Screen Vision
        res_vis = user32.RegisterHotKey(None, HOTKEY_ID_VISION, MOD_CTRL | MOD_SHIFT | MOD_NOREPEAT, VK_S)
        if not res_vis:
            res_vis = user32.RegisterHotKey(None, HOTKEY_ID_VISION, MOD_CTRL | MOD_SHIFT, VK_S)
        
        # Register Ctrl+Shift+Space for Push-to-Talk / Wake Mochi
        res_vox = user32.RegisterHotKey(None, HOTKEY_ID_VOICE, MOD_CTRL | MOD_SHIFT | MOD_NOREPEAT, VK_SPACE)
        if not res_vox:
            res_vox = user32.RegisterHotKey(None, HOTKEY_ID_VOICE, MOD_CTRL | MOD_SHIFT, VK_SPACE)
            
        print(f"[Global Hotkeys] Ctrl+Shift+S (Vision): {'Active' if res_vis else 'Unavailable'}, Ctrl+Shift+Space (Voice): {'Active' if res_vox else 'Unavailable'}")
        
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == 0x0312: # WM_HOTKEY
                if msg.wParam == HOTKEY_ID_VISION:
                    controller.sig_hotkey_vision.emit()
                elif msg.wParam == HOTKEY_ID_VOICE:
                    controller.sig_hotkey_voice.emit()
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    except Exception as e:
        print("[Global Hotkey Engine Warning]", e)

def main():
    app = QApplication(sys.argv)
    controller = WindowController()

    # Start global hotkeys in daemon thread
    hotkey_thread = threading.Thread(target=start_global_hotkeys, args=(controller,), daemon=True)
    hotkey_thread.start()

    # Start tracker and server in background thread, linked to controller
    server_thread = threading.Thread(target=start_backend, args=(controller,), daemon=True)
    server_thread.start()

    # Ensure FastAPI is fully listening before loading QWebEngineView
    wait_for_server()

    dock = NativeFloatingDock()
    controller.set_window(dock)
    dock.web_view.load(QUrl("http://127.0.0.1:8765"))
    dock.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
