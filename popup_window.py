"""
Ventana emergente flotante (Popup) para mostrar la traducción local instantánea.
Incluye:
- Auto-ajuste dinámico de ancho y alto según el tamaño del texto.
- Arrastre fluido de la ventana con el ratón por toda la pantalla.
- Soporte para 5 temas visuales y control de opacidad/transparencia.
- Botones rápidos: Copiar, Fijar (Pin), Invertir y Cerrar.
"""

from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QRect
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QGraphicsDropShadowEffect, QFrame, QSizePolicy
)
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QCursor, QTextDocument
import pyperclip

class HeaderBar(QFrame):
    """Barra superior arrastrable con el ratón."""
    def __init__(self, parent_popup):
        super().__init__()
        self.popup = parent_popup
        self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.popup.start_drag(event.globalPosition().toPoint())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.popup.do_drag(event.globalPosition().toPoint())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.popup.end_drag()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

class TranslationPopup(QWidget):
    request_retranslate = pyqtSignal(str, str) # text, forced_source

    def __init__(self, theme_data=None, opacity_percent=94):
        super().__init__()
        self.is_pinned = False
        self.was_manually_moved = False
        self._is_dragging = False
        self._drag_start_offset = QPoint(0, 0)
        self.theme_data = theme_data

        self.current_raw_text = ""
        self.current_source_lang = "en"
        self.current_target_lang = "es"

        self._init_ui()
        self.set_popup_opacity(opacity_percent)

    def _init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Contenedor principal con sombra
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.card = QFrame(self)
        self.card.setObjectName("card")

        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(14, 10, 14, 14)
        self.card_layout.setSpacing(8)

        # --- BARRA SUPERIOR (HEADER) ---
        self.header_frame = HeaderBar(self)
        self.header_frame.setStyleSheet("background: transparent;")
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        # Icono indicador de arrastre
        self.drag_hint = QLabel("⠿", self.header_frame)
        self.drag_hint.setToolTip("Arrastra desde aquí para mover la ventana")
        header_layout.addWidget(self.drag_hint)

        # Insignia de idioma (EN -> ES)
        self.lang_badge = QLabel("EN ➔ ES", self.header_frame)
        header_layout.addWidget(self.lang_badge)

        # Botón invertir idioma
        self.swap_btn = QPushButton("⇄", self.header_frame)
        self.swap_btn.setFixedSize(24, 22)
        self.swap_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.swap_btn.setToolTip("Invertir dirección de traducción")
        self.swap_btn.clicked.connect(self._swap_languages)
        header_layout.addWidget(self.swap_btn)

        # Badge de privacidad Offline
        self.offline_badge = QLabel("🔒 Offline", self.header_frame)
        header_layout.addWidget(self.offline_badge)
        header_layout.addStretch()

        # Botón Copiar
        self.copy_btn = QPushButton("📋 Copiar", self.header_frame)
        self.copy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.copy_btn.setToolTip("Copiar traducción al portapapeles")
        self.copy_btn.clicked.connect(self._copy_translation)
        header_layout.addWidget(self.copy_btn)

        # Botón Fijar (Pin)
        self.pin_btn = QPushButton("📌", self.header_frame)
        self.pin_btn.setFixedSize(24, 22)
        self.pin_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.pin_btn.setToolTip("Fijar ventana (evita que se cierre al hacer clic fuera)")
        self.pin_btn.clicked.connect(self._toggle_pin)
        header_layout.addWidget(self.pin_btn)

        # Botón Cerrar
        self.close_btn = QPushButton("✕", self.header_frame)
        self.close_btn.setFixedSize(24, 22)
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.setToolTip("Cerrar (Esc)")
        self.close_btn.clicked.connect(self.hide)
        header_layout.addWidget(self.close_btn)

        self.card_layout.addWidget(self.header_frame)

        # --- TEXTO ORIGINAL ---
        self.src_label = QLabel("Original:", self.card)
        self.card_layout.addWidget(self.src_label)

        self.src_text_edit = QTextEdit(self.card)
        self.src_text_edit.setReadOnly(True)
        self.card_layout.addWidget(self.src_text_edit)

        # --- TEXTO TRADUCIDO ---
        self.dst_label = QLabel("Traducción:", self.card)
        self.card_layout.addWidget(self.dst_label)

        self.dst_text_edit = QTextEdit(self.card)
        self.dst_text_edit.setReadOnly(False)
        self.card_layout.addWidget(self.dst_text_edit)

        # Sombra del card
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(22)
        self.shadow.setColor(QColor(0, 0, 0, 160))
        self.shadow.setOffset(0, 6)
        self.card.setGraphicsEffect(self.shadow)

        main_layout.addWidget(self.card)
        self.resize(420, 280)

        if self.theme_data:
            self.apply_theme(self.theme_data)

    def set_popup_opacity(self, percent: int):
        """Ajusta la opacidad / transparencia de la ventana flotante."""
        val = max(50, min(100, percent)) / 100.0
        self.setWindowOpacity(val)

    def apply_theme(self, theme: dict):
        self.theme_data = theme
        card_bg = theme.get("card_bg", "#121214")
        border = theme.get("border", "#27272a")
        border_focus = theme.get("border_focus", "#52525b")
        text_primary = theme.get("text_primary", "#f4f4f5")
        text_secondary = theme.get("text_secondary", "#a1a1aa")
        badge_bg = theme.get("badge_bg", "#3f3f46")
        badge_text = theme.get("badge_text", "#f4f4f5")
        btn_bg = theme.get("btn_bg", "#27272a")
        btn_hover = theme.get("btn_hover", "#3f3f46")
        btn_text = theme.get("btn_text", "#e4e4e7")
        input_bg = theme.get("input_bg", "#09090b")

        self.card.setStyleSheet(f"""
            QFrame#card {{
                background-color: {card_bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
        """)

        self.drag_hint.setStyleSheet(f"color: {text_secondary}; font-size: 16px; font-weight: bold;")

        self.lang_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {badge_bg};
                color: {badge_text};
                font-weight: bold;
                font-size: 11px;
                padding: 3px 8px;
                border-radius: 6px;
                border: 1px solid {border};
            }}
        """)

        self.offline_badge.setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold; padding-left: 2px;")

        btn_style = f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_text};
                font-size: 11px;
                padding: 3px 8px;
                border: 1px solid {border};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                color: {text_primary};
                border: 1px solid {border_focus};
            }}
        """
        self.swap_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_text};
                font-size: 13px;
                font-weight: bold;
                border: 1px solid {border};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                border: 1px solid {border_focus};
            }}
        """)
        self.copy_btn.setStyleSheet(btn_style)

        if not self.is_pinned:
            self.pin_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {btn_bg};
                    color: {text_secondary};
                    font-size: 11px;
                    border: 1px solid {border};
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    background-color: {btn_hover};
                    border: 1px solid {border_focus};
                }}
            """)
        else:
            self.pin_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {badge_bg};
                    color: {badge_text};
                    font-size: 11px;
                    border: 1px solid {border_focus};
                    border-radius: 4px;
                }}
            """)

        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {text_secondary};
                font-size: 12px;
                font-weight: bold;
                border: 1px solid {border};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #ef4444;
                color: #ffffff;
                border: 1px solid #ef4444;
            }}
        """)

        self.src_label.setStyleSheet(f"color: {text_secondary}; font-size: 10px; font-weight: bold;")
        self.dst_label.setStyleSheet(f"color: {badge_text}; font-size: 10px; font-weight: bold;")

        self.src_text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {input_bg};
                color: {text_secondary};
                border: 1px solid {border};
                border-radius: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                padding: 6px;
            }}
        """)

        self.dst_text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {input_bg};
                color: {text_primary};
                border: 1px solid {border};
                border-radius: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                line-height: 1.45;
                padding: 8px;
            }}
            QTextEdit:focus {{
                border: 1px solid {border_focus};
            }}
        """)

    # --- GESTIÓN DE ARRASTRE DE VENTANA CON EL RATÓN ---
    def start_drag(self, global_pt: QPoint):
        self._is_dragging = True
        self._drag_start_offset = global_pt - self.pos()
        self.was_manually_moved = True
        if not self.is_pinned:
            self._toggle_pin()

    def do_drag(self, global_pt: QPoint):
        if self._is_dragging:
            self.move(global_pt - self._drag_start_offset)

    def end_drag(self):
        self._is_dragging = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_drag(event.globalPosition().toPoint())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            self.do_drag(event.globalPosition().toPoint())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.end_drag()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    # --- AJUSTE DINÁMICO DE TAMAÑO SEGÚN CONTENIDO ---
    def _compute_and_apply_dynamic_size(self, orig_text: str, trans_text: str, ref_pos: QPoint):
        screen = QGuiApplication.screenAt(ref_pos) or QGuiApplication.primaryScreen()
        screen_geom = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)

        max_allowed_w = min(720, int(screen_geom.width() * 0.72))
        max_allowed_h = min(680, int(screen_geom.height() * 0.80))
        min_w = 400
        min_h = 260

        total_chars = max(len(orig_text), len(trans_text))

        if total_chars > 350:
            target_w = min(max_allowed_w, 600)
        elif total_chars > 160:
            target_w = min(max_allowed_w, 480)
        else:
            target_w = min_w

        content_w = target_w - 52

        doc_src = QTextDocument()
        doc_src.setDefaultFont(self.src_text_edit.font())
        doc_src.setPlainText(orig_text)
        doc_src.setTextWidth(content_w)
        ideal_src_h = int(doc_src.size().height()) + 20
        src_h = max(45, min(140, ideal_src_h))

        doc_dst = QTextDocument()
        doc_dst.setDefaultFont(self.dst_text_edit.font())
        doc_dst.setPlainText(trans_text)
        doc_dst.setTextWidth(content_w)
        ideal_dst_h = int(doc_dst.size().height()) + 24
        dst_h = max(75, min(380, ideal_dst_h))

        self.src_text_edit.setFixedHeight(src_h)
        self.dst_text_edit.setFixedHeight(dst_h)

        total_h = min(max_allowed_h, max(min_h, src_h + dst_h + 120))
        self.resize(target_w, total_h)

    def display_translation(self, original_text: str, translated_text: str, src_lang: str, dst_lang: str, near_pos: QPoint):
        self.current_raw_text = original_text
        self.current_source_lang = src_lang
        self.current_target_lang = dst_lang

        self.src_text_edit.setPlainText(original_text)
        self.dst_text_edit.setPlainText(translated_text)
        self.lang_badge.setText(f"{src_lang.upper()} ➔ {dst_lang.upper()}")

        self._compute_and_apply_dynamic_size(original_text, translated_text, near_pos)

        if not self.was_manually_moved:
            self._position_near(near_pos)

        self.show()
        self.raise_()
        self.activateWindow()

    def set_loading(self, original_text: str, near_pos: QPoint):
        self.current_raw_text = original_text
        self.src_text_edit.setPlainText(original_text)
        self.dst_text_edit.setPlainText("Traduciendo con modelo local...")

        self._compute_and_apply_dynamic_size(original_text, "Traduciendo con modelo local...", near_pos)

        if not self.was_manually_moved:
            self._position_near(near_pos)

        self.show()
        self.raise_()

    def _position_near(self, pos: QPoint):
        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        geom = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)

        target_x = pos.x() + 10
        target_y = pos.y() + 10

        if target_x + self.width() > geom.right():
            target_x = max(geom.left() + 10, pos.x() - self.width() - 10)
        if target_y + self.height() > geom.bottom():
            target_y = max(geom.top() + 10, pos.y() - self.height() - 10)

        self.move(target_x, target_y)

    def _toggle_pin(self):
        self.is_pinned = not self.is_pinned
        if self.theme_data:
            self.apply_theme(self.theme_data)

    def _swap_languages(self):
        new_source = self.current_target_lang
        self.request_retranslate.emit(self.current_raw_text, new_source)

    def _copy_translation(self):
        translated = self.dst_text_edit.toPlainText()
        if translated:
            try:
                pyperclip.copy(translated)
                self.copy_btn.setText("✔ Copiado")
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(1500, lambda: self.copy_btn.setText("📋 Copiar"))
            except Exception:
                pass

    def dismiss_if_unpinned(self):
        if not self.is_pinned and self.isVisible():
            self.hide()
            self.was_manually_moved = False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.was_manually_moved = False
        else:
            super().keyPressEvent(event)
