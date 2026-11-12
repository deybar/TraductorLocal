"""
Botón flotante en miniatura que aparece cerca del cursor al seleccionar texto.
Diseño compacto, discreto y estilizado con soporte de temas visuales.
"""

import ctypes
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QGraphicsDropShadowEffect
from PyQt6.QtGui import QColor, QCursor, QFont, QGuiApplication

class FloatingTranslateButton(QWidget):
    clicked_translate = pyqtSignal(str, QPoint)

    def __init__(self, theme_data=None):
        super().__init__()
        self.selected_text = ""
        self.theme_data = theme_data
        self._init_ui()

        # Temporizador para ocultar si el usuario no interactúa
        self.auto_hide_timer = QTimer(self)
        self.auto_hide_timer.setInterval(3800)
        self.auto_hide_timer.setSingleShot(True)
        self.auto_hide_timer.timeout.connect(self.hide_button)

    def _init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)

        # Botón compacto (26x26 px)
        self.btn = QPushButton("文A", self)
        self.btn.setFixedSize(26, 26)
        self.btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn.setToolTip("Traducir selección (100% Local / Offline)")

        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        self.btn.setFont(font)

        # Sombra sutil y discreta
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(8)
        self.shadow.setColor(QColor(0, 0, 0, 110))
        self.shadow.setOffset(0, 2)
        self.btn.setGraphicsEffect(self.shadow)

        self.btn.clicked.connect(self._on_clicked)
        layout.addWidget(self.btn)
        self.setFixedSize(34, 34)

        if self.theme_data:
            self.apply_theme(self.theme_data)
        else:
            self._apply_default_style()

    def _apply_default_style(self):
        self.btn.setStyleSheet("""
            QPushButton {
                background-color: #27272a;
                color: #e4e4e7;
                border: 1px solid #44444a;
                border-radius: 13px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #3f3f46;
                color: #ffffff;
                border: 1px solid #52525b;
            }
            QPushButton:pressed {
                background-color: #18181b;
            }
        """)

    def apply_theme(self, theme: dict):
        self.theme_data = theme
        bg = theme.get("icon_bg", "#27272a")
        border = theme.get("icon_border", "#44444a")
        hover = theme.get("icon_hover", "#3f3f46")
        text = theme.get("icon_text", "#f4f4f5")

        self.btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 13px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {hover};
                border: 1px solid {text};
                color: {text};
            }}
            QPushButton:pressed {{
                background-color: {bg};
            }}
        """)

    def show_at(self, text: str, x: int, y: int):
        if not text or not text.strip():
            return

        self.selected_text = text.strip()

        # Posicionar discretamente cerca del cursor
        target_x = x + 12
        target_y = y - 40

        screen = QGuiApplication.screenAt(QPoint(x, y)) or QGuiApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            if target_x + self.width() > geom.right():
                target_x = x - self.width() - 8
            if target_y < geom.top():
                target_y = y + 20

        self.move(target_x, target_y)
        self.show()
        self.raise_()

        try:
            HWND_TOPMOST = -1
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            SWP_SHOWWINDOW = 0x0040
            ctypes.windll.user32.SetWindowPos(
                int(self.winId()), HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
            )
        except Exception:
            pass

        self.auto_hide_timer.start()

    def hide_button(self):
        self.auto_hide_timer.stop()
        self.hide()
        self.selected_text = ""

    def enterEvent(self, event):
        self.auto_hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.isVisible():
            self.auto_hide_timer.start()
        super().leaveEvent(event)

    def _on_clicked(self):
        txt = self.selected_text
        pos = self.pos()
        self.hide_button()
        self.clicked_translate.emit(txt, pos)
