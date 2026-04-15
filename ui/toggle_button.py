"""
桌面悬浮切换按钮
- 始终置顶，不抢焦点
- 点击切换宠物显示/隐藏
- 可拖拽移动位置
"""
import ctypes
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore    import Qt, QPoint, pyqtSignal
from PyQt6.QtGui     import QPainter, QColor, QFont

WS_EX_NOACTIVATE   = 0x08000000
WS_EX_TOOLWINDOW   = 0x00000080
GWL_EXSTYLE        = -20


class ToggleButton(QWidget):
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._drag_pos = None
        self._visible_state = True   # 当前宠物是否显示
        self._setup_window()
        self._build_ui()
        self._apply_noactivate()

        # 默认放在右下角
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 90, screen.height() - 160)

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
        self.setFixedSize(72, 28)

    def _build_ui(self):
        self._label = QLabel("🐾 宠物", self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setGeometry(0, 0, 72, 28)
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        self._label.setFont(font)

    def _apply_noactivate(self):
        try:
            hwnd = int(self.winId())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(
                hwnd, GWL_EXSTYLE,
                style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
            )
        except Exception:
            pass

    def set_state(self, pet_visible: bool):
        """同步宠物状态"""
        self._visible_state = pet_visible
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._visible_state:
            bg = QColor(30, 20, 10, 200)
            border = QColor(201, 168, 76, 220)   # 金色
            text_color = QColor(240, 220, 160)
        else:
            bg = QColor(20, 20, 20, 180)
            border = QColor(100, 100, 100, 180)   # 灰色
            text_color = QColor(160, 160, 160)

        p.setBrush(bg)
        p.setPen(border)
        p.drawRoundedRect(1, 1, self.width()-2, self.height()-2, 8, 8)

        p.setPen(text_color)
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        p.setFont(font)
        text = "🐾 宠物" if self._visible_state else "🐾 显示"
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)

    # ── 拖拽 ──────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            # 移动距离很小才算点击
            if self._drag_pos:
                delta = e.globalPosition().toPoint() - self.frameGeometry().topLeft() - self._drag_pos
                if abs(delta.x()) < 5 and abs(delta.y()) < 5:
                    self.clicked.emit()
            self._drag_pos = None
