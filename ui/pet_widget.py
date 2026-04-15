"""
桌面宠物主窗口 v2。
- 无边框、透明背景、始终置顶、可拖拽
- 点击不抢焦点（全屏游戏不会被切走）
- 圆形可爱图标 + 情绪光晕
- Phase2: 呼吸动画、粒子效果、HP关联视觉、情绪过渡
"""
import os, ctypes, math, random
from PyQt6.QtWidgets import QWidget, QApplication, QMenu
from PyQt6.QtCore    import Qt, QTimer, QPoint, QRectF
from PyQt6.QtGui     import (QPixmap, QPainter, QColor, QBrush, QPen,
                              QRadialGradient, QAction, QPainterPath, QFont)

SPRITE_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "sprites")

CHARACTER_ICON = {
    "IRONCLAD":   "ironclad_icon.png",
    "THE_SILENT": "silent_icon.png",
    "DEFECT":     "defect_icon.png",
    "WATCHER":    "watcher_icon.png",
}

# 情绪 → 光晕颜色
MOOD_GLOW = {
    "happy":    QColor(255, 215,  80, 160),   # 金色
    "normal":   QColor(180, 140,  80,  80),   # 暗金
    "worried":  QColor(255, 140,  30, 180),   # 橙色
    "alert":    QColor(220,  50,  50, 200),   # 红色
    "sleep":    QColor( 80, 100, 220, 120),   # 蓝紫
    "critical": QColor(180,  20,  20, 220),   # 深红
    "strong":   QColor( 80, 220,  80, 140),   # 绿色
}

ICON_SIZE  = 128  # circle icon diameter (px)
GLOW_PAD   = 20   # glow expansion (px)
WIDGET_SIZE = ICON_SIZE + GLOW_PAD * 2


# ── 粒子 ────────────────────────────────────────────────
class _Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life",
                 "size", "color", "shape")

    def __init__(self, x, y, vx, vy, life, size, color, shape="dot"):
        self.x = x; self.y = y
        self.vx = vx; self.vy = vy
        self.life = life; self.max_life = life
        self.size = size; self.color = color
        self.shape = shape

    def tick(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        return self.life > 0


class PetWidget(QWidget):
    def __init__(self, on_click=None, on_quit=None, on_move=None, on_toggle=None):
        super().__init__()
        self._on_click  = on_click
        self._on_quit   = on_quit
        self._on_move   = on_move
        self._on_toggle = on_toggle
        self._mood      = "normal"
        self._target_mood = "normal"
        self._character = None
        self._raw_pixmap = None
        self._drag_pos   = None
        self._click_origin = None
        self._is_dragging = False

        # Animation state
        self._bob_t      = 0.0
        self._bob_offset = 0
        self._alert_t   = 0
        self._breath_t  = 0.0       # breathing animation phase
        self._breath_scale = 1.0    # current scale factor
        self._glow_pulse_t = 0.0    # glow pulsing
        self._hp_ratio  = 1.0       # for HP-linked visuals
        self._particles: list[_Particle] = []
        self._particle_timer = 0

        # Mood transition
        self._mood_blend = 0.0      # 0.0 = old mood, 1.0 = new mood
        self._old_mood = "normal"

        self._setup_window()
        self._setup_timer()
        self._load_icon("IRONCLAD")

    # ── 窗口初始化 ────────────────────────────────────────
    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint      |
            Qt.WindowType.WindowStaysOnTopHint     |
            Qt.WindowType.Tool                     |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.resize(WIDGET_SIZE, WIDGET_SIZE)

        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - WIDGET_SIZE - 40,
                  screen.height() - WIDGET_SIZE - 80)

    def _apply_noactivate_flag(self):
        try:
            GWL_EXSTYLE      = -20
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_TOOLWINDOW = 0x00000080
            hwnd = int(self.winId())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            )
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_noactivate_flag()

    # ── 动画定时器 ────────────────────────────────────────
    def _setup_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(80)   # ~12 fps

    def _tick(self):
        self._bob_t += 0.07
        self._breath_t += 0.04
        self._glow_pulse_t += 0.05

        # Breathing scale (subtle 2% oscillation)
        if self._mood == "sleep":
            self._breath_scale = 1.0 + math.sin(self._breath_t * 0.5) * 0.03
        elif self._mood == "alert" or self._mood == "critical":
            self._breath_scale = 1.0 + math.sin(self._breath_t * 2.0) * 0.015
        else:
            self._breath_scale = 1.0 + math.sin(self._breath_t) * 0.02

        # Mood transition blending
        if self._mood_blend < 1.0:
            self._mood_blend = min(1.0, self._mood_blend + 0.08)

        # Bob offset by mood
        if self._mood == "alert" or self._mood == "critical":
            self._alert_t += 1
            offset = int(math.sin(self._alert_t * 0.7) * 9)
            if self._alert_t > 50:
                self._alert_t = 0
                if self._mood == "alert":
                    self._mood = "worried"
        elif self._mood == "sleep":
            offset = int(math.sin(self._bob_t * 0.3) * 2)
        elif self._mood == "worried":
            offset = int(math.sin(self._bob_t * 1.4) * 4)
        elif self._mood == "happy" or self._mood == "strong":
            offset = int(math.sin(self._bob_t * 1.1) * 6)
        else:
            offset = int(math.sin(self._bob_t) * 5)

        pos = self.pos()
        new_y = pos.y() + offset - self._bob_offset
        self.move(pos.x(), new_y)
        self._bob_offset = offset

        # Spawn particles
        self._particle_timer += 1
        self._spawn_mood_particles()

        # Tick particles
        self._particles = [p for p in self._particles if p.tick()]

        self.update()

    def _spawn_mood_particles(self):
        cx = WIDGET_SIZE / 2
        cy = WIDGET_SIZE / 2
        r = ICON_SIZE / 2

        if self._mood == "happy" or self._mood == "strong":
            if self._particle_timer % 6 == 0:
                # Golden sparkles rising
                angle = random.uniform(0, math.pi * 2)
                dist = random.uniform(r * 0.4, r * 1.1)
                px = cx + math.cos(angle) * dist
                py = cy + math.sin(angle) * dist
                color = QColor(255, 215, random.randint(60, 120),
                               random.randint(140, 220))
                self._particles.append(_Particle(
                    px, py, random.uniform(-0.3, 0.3), random.uniform(-1.5, -0.5),
                    random.randint(12, 22), random.uniform(2, 4), color, "star"))

        elif self._mood == "worried":
            if self._particle_timer % 15 == 0:
                # Sweat drops
                px = cx + random.uniform(-r * 0.3, r * 0.3)
                py = cy - r * 0.6
                color = QColor(150, 200, 255, 180)
                self._particles.append(_Particle(
                    px, py, random.uniform(-0.2, 0.2), 1.2,
                    random.randint(15, 25), 3, color, "drop"))

        elif self._mood == "alert" or self._mood == "critical":
            if self._particle_timer % 4 == 0:
                # Red sparks
                angle = random.uniform(0, math.pi * 2)
                dist = r * 0.9
                px = cx + math.cos(angle) * dist
                py = cy + math.sin(angle) * dist
                color = QColor(255, random.randint(30, 80), 30,
                               random.randint(150, 230))
                self._particles.append(_Particle(
                    px, py,
                    math.cos(angle) * random.uniform(0.5, 1.5),
                    math.sin(angle) * random.uniform(0.5, 1.5),
                    random.randint(8, 15), random.uniform(2, 3.5), color, "dot"))

        elif self._mood == "sleep":
            if self._particle_timer % 25 == 0:
                # Zzz floating up
                px = cx + r * 0.4
                py = cy - r * 0.3
                color = QColor(130, 160, 255, 160)
                self._particles.append(_Particle(
                    px, py, 0.3, -0.8,
                    random.randint(25, 40), 0, color, "zzz"))

    # ── 立绘加载 ─────────────────────────────────────────
    def _load_icon(self, character: str):
        filename = CHARACTER_ICON.get(character, "ironclad_icon.png")
        path = os.path.join(SPRITE_DIR, filename)
        if os.path.exists(path):
            self._raw_pixmap = QPixmap(path)
        else:
            self._raw_pixmap = None
        self._character = character
        self.update()

    # ── 绘制 ─────────────────────────────────────────────
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        cx = WIDGET_SIZE / 2
        cy = WIDGET_SIZE / 2
        r  = ICON_SIZE  / 2

        # ── 光晕（带脉冲） ──────────────────────────────
        glow_color = self._get_blended_glow()
        pulse = 1.0 + math.sin(self._glow_pulse_t) * 0.15
        glow_r = (r + GLOW_PAD) * pulse

        grad = QRadialGradient(cx, cy, glow_r)
        grad.setColorAt(0.55, glow_color)
        grad.setColorAt(1.0,  QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(cx - glow_r, cy - glow_r,
                                   glow_r * 2, glow_r * 2))

        # ── HP ring (subtle arc behind the icon) ─────────
        if self._hp_ratio < 1.0:
            self._draw_hp_ring(painter, cx, cy, r)

        # ── 圆形裁剪区域（带呼吸缩放）────────────────────
        scale = self._breath_scale
        sr = r * scale
        clip_path = QPainterPath()
        clip_path.addEllipse(QRectF(cx - sr, cy - sr, sr * 2, sr * 2))
        painter.setClipPath(clip_path)

        # ── 深色背景圆 ────────────────────────────────────
        painter.setBrush(QBrush(QColor(30, 20, 10, 220)))
        painter.drawEllipse(QRectF(cx - sr, cy - sr, sr * 2, sr * 2))

        # ── 角色图标 ──────────────────────────────────────
        if self._raw_pixmap:
            icon_sz = int(sr * 2)
            scaled = self._raw_pixmap.scaled(
                icon_sz, icon_sz,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            ox = cx - scaled.width()  / 2
            oy = cy - scaled.height() / 2
            painter.drawPixmap(int(ox), int(oy), scaled)

            # HP tint overlay (darken when low HP)
            if self._hp_ratio < 0.35:
                tint_alpha = int((0.35 - self._hp_ratio) * 200)
                painter.setBrush(QBrush(QColor(80, 0, 0, min(tint_alpha, 80))))
                painter.drawEllipse(QRectF(cx - sr, cy - sr, sr * 2, sr * 2))
        else:
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(QRectF(cx-sr, cy-sr, sr*2, sr*2),
                             Qt.AlignmentFlag.AlignCenter, "🎮")

        painter.setClipping(False)

        # ── 边框环 ────────────────────────────────────────
        border_color = self._get_border_color()
        pen = QPen(border_color, 3)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(cx - sr + 1.5, cy - sr + 1.5,
                                   sr * 2 - 3, sr * 2 - 3))

        # ── 粒子绘制 ─────────────────────────────────────
        self._draw_particles(painter)

        # ── 情绪小徽章（右下角）──────────────────────────
        badge = {
            "happy": "😊", "normal": "😐", "worried": "😰",
            "alert": "😱", "sleep": "😴", "critical": "💀",
            "strong": "😎",
        }.get(self._mood)
        if badge:
            f = QFont(); f.setPointSize(18)
            painter.setFont(f)
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(QRectF(cx + sr - 28, cy + sr - 28, 30, 30),
                             Qt.AlignmentFlag.AlignCenter, badge)

        painter.end()

    def _get_blended_glow(self) -> QColor:
        """Blend between old and new mood glow colors during transition."""
        new_glow = MOOD_GLOW.get(self._mood, MOOD_GLOW["normal"])

        if self._mood == "alert" or self._mood == "critical":
            alpha = int(120 + math.sin(self._alert_t * 0.4) * 80)
            base = QColor(220, 50, 50) if self._mood == "alert" else QColor(180, 20, 20)
            new_glow = QColor(base.red(), base.green(), base.blue(),
                              max(0, min(255, alpha)))

        if self._mood_blend >= 1.0 or self._old_mood == self._mood:
            return new_glow

        old_glow = MOOD_GLOW.get(self._old_mood, MOOD_GLOW["normal"])
        b = self._mood_blend
        return QColor(
            int(old_glow.red()   * (1-b) + new_glow.red()   * b),
            int(old_glow.green() * (1-b) + new_glow.green() * b),
            int(old_glow.blue()  * (1-b) + new_glow.blue()  * b),
            int(old_glow.alpha() * (1-b) + new_glow.alpha() * b),
        )

    def _get_border_color(self) -> QColor:
        colors = {
            "happy":    QColor(255, 215, 80),
            "normal":   QColor(160, 120, 50),
            "worried":  QColor(255, 140, 30),
            "alert":    QColor(220,  50, 50),
            "sleep":    QColor( 80, 100, 200),
            "critical": QColor(180,  20, 20),
            "strong":   QColor( 80, 200, 80),
        }
        return colors.get(self._mood, QColor(160, 120, 50))

    def _draw_hp_ring(self, painter: QPainter, cx, cy, r):
        """Draw a subtle HP arc behind the icon."""
        ring_r = r + 6
        rect = QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2)

        # Background arc (dark)
        pen_bg = QPen(QColor(40, 40, 40, 100), 3)
        painter.setPen(pen_bg)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(rect, 90 * 16, -360 * 16)

        # HP arc (colored)
        if self._hp_ratio > 0.6:
            hp_color = QColor(80, 200, 80, 160)
        elif self._hp_ratio > 0.3:
            hp_color = QColor(255, 180, 30, 160)
        else:
            hp_color = QColor(220, 50, 50, 180)

        pen_hp = QPen(hp_color, 3)
        painter.setPen(pen_hp)
        span = int(-360 * self._hp_ratio * 16)
        painter.drawArc(rect, 90 * 16, span)

    def _draw_particles(self, painter: QPainter):
        for p in self._particles:
            alpha = int(255 * (p.life / p.max_life))
            c = QColor(p.color.red(), p.color.green(), p.color.blue(),
                       min(alpha, p.color.alpha()))

            if p.shape == "dot":
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(c))
                painter.drawEllipse(QRectF(p.x - p.size, p.y - p.size,
                                           p.size * 2, p.size * 2))
            elif p.shape == "star":
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(c))
                s = p.size
                # 4-pointed star
                path = QPainterPath()
                path.moveTo(p.x, p.y - s)
                path.lineTo(p.x + s * 0.3, p.y - s * 0.3)
                path.lineTo(p.x + s, p.y)
                path.lineTo(p.x + s * 0.3, p.y + s * 0.3)
                path.lineTo(p.x, p.y + s)
                path.lineTo(p.x - s * 0.3, p.y + s * 0.3)
                path.lineTo(p.x - s, p.y)
                path.lineTo(p.x - s * 0.3, p.y - s * 0.3)
                path.closeSubpath()
                painter.drawPath(path)

            elif p.shape == "drop":
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(c))
                path = QPainterPath()
                path.moveTo(p.x, p.y - p.size)
                path.cubicTo(p.x + p.size, p.y,
                             p.x + p.size * 0.5, p.y + p.size,
                             p.x, p.y + p.size)
                path.cubicTo(p.x - p.size * 0.5, p.y + p.size,
                             p.x - p.size, p.y,
                             p.x, p.y - p.size)
                painter.drawPath(path)

            elif p.shape == "zzz":
                f = QFont()
                sz = 8 + int((1 - p.life / p.max_life) * 6)
                f.setPointSize(sz)
                f.setBold(True)
                painter.setFont(f)
                painter.setPen(c)
                painter.drawText(int(p.x), int(p.y), "Z")

    # ── 公开 API ─────────────────────────────────────────
    def set_character(self, character: str):
        if character != self._character:
            self._load_icon(character)

    def set_mood(self, mood: str):
        if mood != self._mood:
            self._old_mood = self._mood
            self._mood = mood
            self._mood_blend = 0.0  # start transition
            if mood in ("alert", "critical"):
                self._alert_t = 0
            self.update()

    def set_hp_ratio(self, ratio: float):
        """Set HP ratio for visual effects (0.0 - 1.0)."""
        self._hp_ratio = max(0.0, min(1.0, ratio))

    def trigger_alert_animation(self):
        self.set_mood("alert")

    # ── 拖拽（不激活窗口）────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._click_origin = event.globalPosition().toPoint()
            self._is_dragging = False
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
        event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            target = event.globalPosition().toPoint() - self._drag_pos
            screen = QApplication.primaryScreen().geometry()
            x = max(0, min(target.x(), screen.width() - self.width()))
            y = max(0, min(target.y(), screen.height() - self.height()))
            self.move(x, y)
            if self._on_move:
                self._on_move()
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._click_origin:
            if not self._is_dragging:
                if self._on_click:
                    self._on_click()
        self._drag_pos = None
        self._click_origin = None
        self._is_dragging = False

    def moveEvent(self, event):
        super().moveEvent(event)

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.NoDropShadowWindowHint)
        menu.setStyleSheet("""
            QMenu {
                background: #1a1209; color: #f0e6d3;
                border: 1px solid #c9a84c; border-radius: 8px;
                padding: 4px; font-size: 13px;
            }
            QMenu::item { padding: 6px 18px; border-radius: 4px; }
            QMenu::item:selected { background: #3a2510; }
            QMenu::separator { height: 1px; background: #444; margin: 3px 8px; }
        """)
        act_info = QAction("Info Panel", self)
        act_info.triggered.connect(lambda: self._on_click() if self._on_click else None)
        act_hide = QAction("Hide Pet", self)
        act_hide.triggered.connect(lambda: self._on_toggle() if self._on_toggle else None)
        act_quit = QAction("Exit", self)
        act_quit.triggered.connect(lambda: self._on_quit() if self._on_quit else None)
        menu.addAction(act_info)
        menu.addAction(act_hide)
        menu.addSeparator()
        menu.addAction(act_quit)
        menu.exec(pos)
