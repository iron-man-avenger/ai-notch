import sys
import math
import time
from PySide6.QtCore import Qt, QTimer, QPoint, QRectF
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QLinearGradient, QRadialGradient
from PySide6.QtWidgets import QApplication, QWidget

import win32con
import win32gui

class TestCrawlerOverlay(QWidget):
    def __init__(self, target_rect=(400, 300, 350, 80), focus="rephrase"):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        self.start_x = screen.width() / 2.0
        self.start_y = 36.0
        self.target_x, self.target_y, self.target_w, self.target_h = target_rect
        self.focus = focus

        # Theme color based on tool
        if focus == "error_diagnosis":
            self.theme_color = QColor(244, 63, 94)  # Rose
            self.label = "ERROR DIAGNOSTIC SCANNER"
        elif focus == "data_extraction":
            self.theme_color = QColor(6, 182, 212)  # Cyan
            self.label = "DATA & FIELD EXTRACTOR"
        elif focus == "teams_reply":
            self.theme_color = QColor(16, 185, 129) # Emerald
            self.label = "REPLY ASSISTANT PROBE"
        else: # rephrase
            self.theme_color = QColor(168, 85, 247) # Purple
            self.label = "TEXT REPHRASE PROBE"

        self.cur_x = self.start_x
        self.cur_y = self.start_y
        self.progress = 0.0 # 0.0 to 1.0 (moving), 1.0 to 2.5 (scanning), 2.5 to 3.0 (fading)
        self.scan_laser_y = 0.0
        self.scan_dir = 1
        self.walk_cycle = 0.0
        self.opacity = 1.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16) # ~60 fps

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_click_through()

    def _apply_click_through(self):
        hwnd = int(self.winId())
        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(
            hwnd,
            win32con.GWL_EXSTYLE,
            ex_style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
        )

    def _tick(self):
        self.progress += 0.018
        self.walk_cycle += 0.35

        if self.progress < 1.0:
            # Easing motion towards target
            t = self.progress
            ease = 1.0 - math.pow(1.0 - t, 3)
            # Aim for top center of target bounding box
            dest_x = self.target_x + self.target_w / 2.0
            dest_y = max(40.0, self.target_y - 30.0)
            self.cur_x = self.start_x + (dest_x - self.start_x) * ease
            self.cur_y = self.start_y + (dest_y - self.start_y) * ease
        elif self.progress < 2.5:
            # Scanning phase: laser sweeps across target box
            scan_speed = 3.5
            self.scan_laser_y += scan_speed * self.scan_dir
            if self.scan_laser_y > self.target_h:
                self.scan_dir = -1
            elif self.scan_laser_y < 0:
                self.scan_dir = 1
        else:
            # Fade out phase
            self.opacity = max(0.0, 1.0 - (self.progress - 2.5) / 0.5)
            if self.opacity <= 0.01:
                self.timer.stop()
                self.close()
                return

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self.opacity)

        col = self.theme_color

        # ── 1. Target Bounding Box & HUD Brackets (when Mochi arrives or getting close) ──
        if self.progress > 0.4:
            hud_alpha = min(1.0, (self.progress - 0.4) / 0.4)
            pen = QPen(QColor(col.red(), col.green(), col.blue(), int(220 * hud_alpha)))
            pen.setWidth(2)
            painter.setPen(pen)

            bx, by, bw, bh = self.target_x, self.target_y, self.target_w, self.target_h
            corner = 18

            # Corner brackets
            # Top-Left
            painter.drawLine(bx, by + corner, bx, by)
            painter.drawLine(bx, by, bx + corner, by)
            # Top-Right
            painter.drawLine(bx + bw - corner, by, bx + bw, by)
            painter.drawLine(bx + bw, by, bx + bw, by + corner)
            # Bottom-Right
            painter.drawLine(bx + bw, by + bh - corner, bx + bw, by + bh)
            painter.drawLine(bx + bw, by + bh, bx + bw - corner, by + bh)
            # Bottom-Left
            painter.drawLine(bx + corner, by + bh, bx, by + bh)
            painter.drawLine(bx, by + bh, bx, by + bh - corner)

            # Laser Sweep Line inside target box
            if self.progress >= 1.0:
                laser_y = by + self.scan_laser_y
                grad = QLinearGradient(bx, laser_y, bx + bw, laser_y)
                grad.setColorAt(0.0, QColor(col.red(), col.green(), col.blue(), 0))
                grad.setColorAt(0.5, QColor(255, 255, 255, 220))
                grad.setColorAt(1.0, QColor(col.red(), col.green(), col.blue(), 0))
                laser_pen = QPen(QBrush(grad), 2)
                painter.setPen(laser_pen)
                painter.drawLine(bx + 4, laser_y, bx + bw - 4, laser_y)

                # Laser glow ribbon
                glow_grad = QLinearGradient(bx, laser_y - 8, bx, laser_y + 8)
                glow_grad.setColorAt(0.0, QColor(col.red(), col.green(), col.blue(), 0))
                glow_grad.setColorAt(0.5, QColor(col.red(), col.green(), col.blue(), 80))
                glow_grad.setColorAt(1.0, QColor(col.red(), col.green(), col.blue(), 0))
                painter.fillRect(QRectF(bx + 4, laser_y - 8, bw - 8, 16), QBrush(glow_grad))

            # HUD Label Pill above target box
            badge_x = bx
            badge_y = max(10, by - 24)
            badge_w = 260
            badge_h = 20
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(15, 17, 23, int(200 * hud_alpha)))
            painter.drawRoundedRect(badge_x, badge_y, badge_w, badge_h, 4, 4)

            # Badge Border
            painter.setPen(QPen(QColor(col.red(), col.green(), col.blue(), int(180 * hud_alpha)), 1))
            painter.drawRoundedRect(badge_x, badge_y, badge_w, badge_h, 4, 4)

            # Badge Text
            painter.setPen(QColor(255, 255, 255, int(240 * hud_alpha)))
            font = QFont("Consolas", 8, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(badge_x + 8, badge_y + 14, f"🎯 {self.label} // LOCKED")

        # ── 2. Animated Mochi Crawler Avatar ──
        mx = self.cur_x
        my = self.cur_y

        # Draw glowing trail from notch
        if self.progress < 1.0:
            trail_pen = QPen(QColor(col.red(), col.green(), col.blue(), 70), 2, Qt.PenStyle.DashLine)
            painter.setPen(trail_pen)
            painter.drawLine(self.start_x, self.start_y, mx, my)

        # Mochi Bot Halo Glow
        radial = QRadialGradient(mx, my, 28)
        radial.setColorAt(0.0, QColor(col.red(), col.green(), col.blue(), 140))
        radial.setColorAt(1.0, QColor(col.red(), col.green(), col.blue(), 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(radial))
        painter.drawEllipse(QPoint(int(mx), int(my)), 28, 28)

        # Mochi Crawler Scuttling Feet
        painter.setPen(QPen(col, 2))
        leg_hop = math.sin(self.walk_cycle) * 4
        # Left Leg
        painter.drawLine(mx - 8, my + 10, mx - 12, my + 18 + leg_hop)
        # Right Leg
        painter.drawLine(mx + 8, my + 10, mx + 12, my + 18 - leg_hop)

        # Mochi Main Rounded Body
        painter.setPen(QPen(QColor(255, 255, 255, 220), 1.5))
        painter.setBrush(QColor(24, 25, 30))
        painter.drawRoundedRect(mx - 15, my - 13, 30, 26, 13, 13)

        # Feature Goggles / Visor (Matching Feature Color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(col)
        painter.drawRoundedRect(mx - 11, my - 8, 22, 9, 4, 4)

        # Mochi Expressive Eyes inside Visor
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(QPoint(int(mx - 5), int(my - 4)), 2, 2)
        painter.drawEllipse(QPoint(int(mx + 5), int(my - 4)), 2, 2)

        # Mochi Antenna on top with pulse light
        painter.setPen(QPen(QColor(255, 255, 255, 180), 1.5))
        painter.drawLine(mx, my - 13, mx, my - 20)
        painter.setBrush(col)
        painter.drawEllipse(QPoint(int(mx), int(my - 21)), 3, 3)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = TestCrawlerOverlay(target_rect=(350, 450, 420, 70), focus="rephrase")
    overlay.show()
    print("Test crawler overlay started.")
    QTimer.singleShot(3500, app.quit) # Auto-exit after 3.5s for test
    sys.exit(app.exec())
