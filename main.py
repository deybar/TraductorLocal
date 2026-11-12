"""
Aplicación Principal: Traductor Local Offline con Selección de Ratón y Popup Flotante.
100% privado, local y seguro.
Incluye:
- Protección contra instancias múltiples (Single Instance Guard).
- Soporte para 5 temas visuales configurables.
- Ajuste de opacidad / transparencia en vivo.
- Icono discreto y compacto cerca del cursor.
- Popup con auto-ajuste y arrastre por la pantalla.
"""

import os
import sys
import threading
import logging

APP_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(APP_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

LOG_FILE = os.path.join(APP_DIR, "traductor.log")
log_handlers = [logging.FileHandler(LOG_FILE, encoding="utf-8", mode="a")]
if sys.stdout is not None:
    log_handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=log_handlers
)
logger = logging.getLogger("TraductorLocal.Main")

from PyQt6.QtCore import Qt, QObject, pyqtSignal, QPoint, QTimer
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QWidget,
    QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel,
    QFrame, QComboBox, QSlider, QGroupBox
)
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QCloseEvent
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from translator_engine import LocalTranslator
from mouse_monitor import SelectionMonitor
from floating_button import FloatingTranslateButton
from popup_window import TranslationPopup
from theme_config import THEMES, load_config, save_config, get_theme_data

SOCKET_NAME = "TraductorLocal_SingleInstance_2026"

def ensure_single_instance(app, on_activate_cb) -> bool:
    """
    Verifica si ya existe otra instancia del programa en ejecución.
    - Si existe: le envía la señal 'ACTIVATE' para traer la ventana existente al frente y retorna False.
    - Si es la primera instancia: crea el servidor local y retorna True.
    """
    test_socket = QLocalSocket()
    test_socket.connectToServer(SOCKET_NAME)
    if test_socket.waitForConnected(400):
        logger.info("Ya existe otra instancia en ejecución. Enviando comando de activación...")
        test_socket.write(b"ACTIVATE")
        test_socket.waitForBytesWritten(400)
        test_socket.disconnectFromServer()
        return False

    # Limpiar posibles sockets huérfanos tras cierres forzados
    QLocalServer.removeServer(SOCKET_NAME)
    server = QLocalServer()
    if server.listen(SOCKET_NAME):
        def handle_connection():
            client = server.nextPendingConnection()
            if client:
                if client.waitForReadyRead(300):
                    data = client.readAll().data().decode("utf-8", errors="ignore")
                    if "ACTIVATE" in data:
                        logger.info("Recibida petición de activación desde otra instancia. Mostrando ventana...")
                        on_activate_cb()
                client.disconnectFromServer()
        server.newConnection.connect(handle_connection)
        app._instance_server = server
        return True
    return True

class SignalBridge(QObject):
    selection_detected = pyqtSignal(str, int, int)
    click_outside = pyqtSignal(int, int)
    translation_ready = pyqtSignal(str, str, str, str, QPoint)
    status_changed = pyqtSignal(str)

class MainWindow(QWidget):
    """Ventana principal que incluye traducción manual y el panel de configuración de apariencia."""
    theme_updated = pyqtSignal(dict)
    opacity_updated = pyqtSignal(int)

    def __init__(self, translator: LocalTranslator, config: dict, on_minimize_to_tray_cb):
        super().__init__()
        self.translator = translator
        self.config = config
        self.on_minimize_to_tray_cb = on_minimize_to_tray_cb

        self.setWindowTitle("Traductor Local Offline (EN ➔ ES / ES ➔ EN)")
        self.setWindowIcon(QIcon(create_tray_icon_pixmap()))
        self.resize(580, 520)
        self._init_ui()
        self.apply_theme(get_theme_data(self.config.get("theme", "Oscuro Clásico (Carbón)")))

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        # Banner informativo de estado
        self.banner = QFrame(self)
        self.banner.setObjectName("banner")
        banner_layout = QVBoxLayout(self.banner)
        banner_layout.setContentsMargins(12, 10, 12, 10)
        banner_layout.setSpacing(4)

        status_lbl = QLabel("🟢 TRADUCTOR LOCAL ACTIVO (OFFLINE / 100% PRIVADO)")
        status_lbl.setStyleSheet("color: #10b981; font-weight: bold; font-size: 13px;")
        banner_layout.addWidget(status_lbl)

        self.help_lbl = QLabel(
            "• Selecciona cualquier texto con el ratón en cualquier ventana para ver el icono [文A].\n"
            "• El popup se auto-ajusta al tamaño del texto y puedes arrastrarlo desde la barra superior."
        )
        self.help_lbl.setStyleSheet("font-size: 11px; line-height: 1.4;")
        banner_layout.addWidget(self.help_lbl)
        main_layout.addWidget(self.banner)

        # --- SECCIÓN: CONFIGURACIÓN VISUAL (TEMAS Y TRANSPARENCIA) ---
        self.config_box = QGroupBox("🎨 Configuración Visual y Apariencia", self)
        config_layout = QVBoxLayout(self.config_box)
        config_layout.setContentsMargins(12, 12, 12, 12)
        config_layout.setSpacing(10)

        # Selector de Tema
        theme_row = QHBoxLayout()
        theme_lbl = QLabel("Tema de color:")
        theme_lbl.setStyleSheet("font-weight: bold;")
        self.theme_combo = QComboBox(self)
        for theme_name in THEMES.keys():
            self.theme_combo.addItem(theme_name)

        curr_theme = self.config.get("theme", "Oscuro Clásico (Carbón)")
        idx = self.theme_combo.findText(curr_theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)

        theme_row.addWidget(theme_lbl)
        theme_row.addWidget(self.theme_combo, 1)
        config_layout.addLayout(theme_row)

        # Selector de Opacidad/Transparencia
        opacity_row = QHBoxLayout()
        opacity_lbl = QLabel("Opacidad del popup:")
        opacity_lbl.setStyleSheet("font-weight: bold;")

        curr_opacity = self.config.get("opacity", 94)
        self.opacity_val_lbl = QLabel(f"{curr_opacity}%")
        self.opacity_val_lbl.setFixedWidth(40)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.opacity_slider.setRange(70, 100)
        self.opacity_slider.setValue(curr_opacity)
        self.opacity_slider.valueChanged.connect(self._on_opacity_slider_changed)

        opacity_row.addWidget(opacity_lbl)
        opacity_row.addWidget(self.opacity_slider, 1)
        opacity_row.addWidget(self.opacity_val_lbl)
        config_layout.addLayout(opacity_row)

        main_layout.addWidget(self.config_box)

        # --- SECCIÓN: PRUEBA MANUAL DE TRADUCCIÓN ---
        self.manual_lbl = QLabel("Prueba rápida manual:")
        main_layout.addWidget(self.manual_lbl)

        self.input_edit = QTextEdit(self)
        self.input_edit.setPlaceholderText("Escribe o pega texto en inglés o español para probar...")
        self.input_edit.setMaximumHeight(75)
        main_layout.addWidget(self.input_edit)

        btn_row = QHBoxLayout()
        self.btn_translate = QPushButton("Traducir Ahora", self)
        self.btn_translate.clicked.connect(self._do_translate)
        btn_row.addWidget(self.btn_translate)

        self.btn_minimize = QPushButton("Minimizar a la Bandeja", self)
        self.btn_minimize.clicked.connect(self.hide)
        btn_row.addWidget(self.btn_minimize)
        btn_row.addStretch()
        main_layout.addLayout(btn_row)

        self.res_lbl = QLabel("Resultado:")
        main_layout.addWidget(self.res_lbl)

        self.output_edit = QTextEdit(self)
        self.output_edit.setReadOnly(True)
        self.output_edit.setMaximumHeight(85)
        main_layout.addWidget(self.output_edit)

    def _on_theme_changed(self, theme_name: str):
        self.config["theme"] = theme_name
        save_config(self.config)
        theme_data = get_theme_data(theme_name)
        self.apply_theme(theme_data)
        self.theme_updated.emit(theme_data)

    def _on_opacity_slider_changed(self, val: int):
        self.config["opacity"] = val
        self.opacity_val_lbl.setText(f"{val}%")
        save_config(self.config)
        self.opacity_updated.emit(val)

    def apply_theme(self, theme: dict):
        bg = theme.get("bg", "#18181b")
        card_bg = theme.get("card_bg", "#121214")
        input_bg = theme.get("input_bg", "#09090b")
        border = theme.get("border", "#27272a")
        border_focus = theme.get("border_focus", "#52525b")
        text_primary = theme.get("text_primary", "#f4f4f5")
        text_secondary = theme.get("text_secondary", "#a1a1aa")
        btn_bg = theme.get("btn_bg", "#27272a")
        btn_hover = theme.get("btn_hover", "#3f3f46")
        btn_text = theme.get("btn_text", "#e4e4e7")
        badge_bg = theme.get("badge_bg", "#3f3f46")

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                color: {text_primary};
                font-family: 'Segoe UI', sans-serif;
            }}
            QGroupBox {{
                background-color: {card_bg};
                border: 1px solid {border};
                border-radius: 8px;
                font-weight: bold;
                margin-top: 10px;
                padding-top: 10px;
                color: {text_primary};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }}
            QFrame#banner {{
                background-color: {card_bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QTextEdit {{
                background-color: {input_bg};
                color: {text_primary};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px;
                font-size: 13px;
            }}
            QTextEdit:focus {{
                border: 1px solid {border_focus};
            }}
            QComboBox {{
                background-color: {btn_bg};
                color: {btn_text};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {card_bg};
                color: {text_primary};
                selection-background-color: {btn_hover};
                border: 1px solid {border};
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_text};
                font-weight: bold;
                border: 1px solid {border};
                border-radius: 6px;
                padding: 7px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                border: 1px solid {border_focus};
                color: {text_primary};
            }}
            QSlider::groove:horizontal {{
                border: 1px solid {border};
                height: 6px;
                background: {input_bg};
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: {badge_bg};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {text_primary};
                border: 1px solid {border};
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }}
        """)
        self.help_lbl.setStyleSheet(f"color: {text_secondary}; font-size: 11px; line-height: 1.4;")

    def _do_translate(self):
        txt = self.input_edit.toPlainText().strip()
        if not txt:
            return
        self.output_edit.setPlainText("Traduciendo localmente...")
        threading.Thread(target=self._worker, args=(txt,), daemon=True).start()

    def _worker(self, txt: str):
        res, src, dst = self.translator.translate(txt)
        QTimer.singleShot(0, lambda: self.output_edit.setPlainText(f"[{src.upper()} ➔ {dst.upper()}]\n{res}"))

    def closeEvent(self, event: QCloseEvent):
        event.ignore()
        self.hide()
        if self.on_minimize_to_tray_cb:
            self.on_minimize_to_tray_cb()

def create_tray_icon_pixmap(color_hex: str = "#27272a") -> QPixmap:
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color_hex))
    painter.setPen(QColor("#52525b"))
    painter.drawRoundedRect(2, 2, 28, 28, 8, 8)

    painter.setPen(QColor("#f4f4f5"))
    painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "文")
    painter.end()
    return pixmap

class ApplicationManager:
    def __init__(self, app: QApplication):
        self.app = app
        self.config = load_config()
        self.active_theme = get_theme_data(self.config.get("theme", "Oscuro Clásico (Carbón)"))

        self.bridge = SignalBridge()

        # Componentes
        self.translator = LocalTranslator(on_status_changed=self._on_translator_status)
        self.floating_btn = FloatingTranslateButton(theme_data=self.active_theme)
        self.popup = TranslationPopup(
            theme_data=self.active_theme,
            opacity_percent=self.config.get("opacity", 94)
        )
        self.main_window = MainWindow(
            self.translator,
            self.config,
            on_minimize_to_tray_cb=self._show_tray_hint
        )

        # Conectar cambios de tema y opacidad en vivo
        self.main_window.theme_updated.connect(self._handle_theme_change)
        self.main_window.opacity_updated.connect(self.popup.set_popup_opacity)

        # Conectar señales del puente
        self.bridge.selection_detected.connect(self._handle_selection)
        self.bridge.click_outside.connect(self._handle_click_outside)
        self.bridge.translation_ready.connect(self._handle_translation_ready)

        # Conectar eventos de widgets
        self.floating_btn.clicked_translate.connect(self._on_button_clicked)
        self.popup.request_retranslate.connect(self._on_retranslate_requested)

        # Monitor de mouse
        self.monitor = SelectionMonitor(
            on_selection_detected=lambda txt, x, y: self.bridge.selection_detected.emit(txt, x, y),
            on_click_outside=lambda x, y: self.bridge.click_outside.emit(x, y)
        )

        self._setup_tray()

    def activate_main_window(self):
        """Restaura y enfoca la ventana principal cuando se intenta abrir una segunda instancia."""
        self.main_window.showNormal()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def _handle_theme_change(self, theme_data: dict):
        self.active_theme = theme_data
        self.floating_btn.apply_theme(theme_data)
        self.popup.apply_theme(theme_data)
        self.tray.setIcon(QIcon(create_tray_icon_pixmap(theme_data.get("badge_bg", "#27272a"))))

    def _show_tray_hint(self):
        self.tray.showMessage(
            "Traductor Local",
            "El traductor sigue funcionando en segundo plano. Selecciona texto en cualquier ventana para traducir.",
            QSystemTrayIcon.MessageIcon.Information,
            2500
        )

    def _on_translator_status(self, msg: str):
        logger.info(f"Estado del motor: {msg}")
        self.bridge.status_changed.emit(msg)

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self.app)
        self.tray.setIcon(QIcon(create_tray_icon_pixmap(self.active_theme.get("badge_bg", "#27272a"))))
        self.tray.setToolTip("Traductor Local Offline (EN ➔ ES / ES ➔ EN)")

        menu = QMenu()

        show_action = menu.addAction("Abrir configuración y traductor...")
        show_action.triggered.connect(self.activate_main_window)

        menu.addSeparator()

        self.status_action = menu.addAction("🟢 Monitoreo de ratón activo")
        self.status_action.setEnabled(False)

        self.toggle_action = menu.addAction("Pausar captura de ratón")
        self.toggle_action.triggered.connect(self._toggle_monitor)

        menu.addSeparator()

        quit_action = menu.addAction("Salir del Traductor")
        quit_action.triggered.connect(self._quit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            if self.main_window.isVisible():
                self.main_window.hide()
            else:
                self.activate_main_window()

    def _toggle_monitor(self):
        if self.monitor.enabled:
            self.monitor.enabled = False
            self.toggle_action.setText("Reanudar captura de ratón")
            self.status_action.setText("🟡 Monitoreo pausado")
            self.floating_btn.hide_button()
            logger.info("Monitoreo de ratón pausado por el usuario.")
        else:
            self.monitor.enabled = True
            self.toggle_action.setText("Pausar captura de ratón")
            self.status_action.setText("🟢 Monitoreo de ratón activo")
            logger.info("Monitoreo de ratón reanudado por el usuario.")

    def _handle_selection(self, text: str, x: int, y: int):
        if not text or len(text.strip()) < 1:
            return
        logger.info(f"Mostrando botón flotante en ({x}, {y}) para texto: {repr(text[:30])}...")
        self.floating_btn.show_at(text, x, y)

    def _handle_click_outside(self, x: int, y: int):
        if self.floating_btn.isVisible():
            btn_rect = self.floating_btn.geometry()
            if not btn_rect.contains(x, y):
                self.floating_btn.hide_button()

        if self.popup.isVisible() and not self.popup.is_pinned:
            popup_rect = self.popup.geometry()
            if not popup_rect.contains(x, y):
                self.popup.dismiss_if_unpinned()

    def _on_button_clicked(self, text: str, pos: QPoint):
        logger.info(f"Clic en botón flotante para traducir: {repr(text[:30])}...")
        self.popup.was_manually_moved = False
        self.popup.set_loading(text, pos)
        threading.Thread(target=self._translate_worker, args=(text, None, pos), daemon=True).start()

    def _on_retranslate_requested(self, text: str, forced_source: str):
        pos = self.popup.pos()
        self.popup.set_loading(text, pos)
        threading.Thread(target=self._translate_worker, args=(text, forced_source, pos), daemon=True).start()

    def _translate_worker(self, text: str, forced_source: str, pos: QPoint):
        translated, src, dst = self.translator.translate(text, forced_source)
        logger.info(f"Traducción completada [{src} -> {dst}]: {repr(translated[:40])}...")
        self.bridge.translation_ready.emit(text, translated, src, dst, pos)

    def _handle_translation_ready(self, orig: str, trans: str, src: str, dst: str, pos: QPoint):
        self.popup.display_translation(orig, trans, src, dst, pos)

    def start(self):
        self.monitor.start()
        self.translator.initialize_models_async()

        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

        logger.info("Aplicación iniciada. Esperando interacciones...")
        return self.app.exec()

    def _quit(self):
        logger.info("Cerrando Traductor Local...")
        self.monitor.stop()
        self.app.quit()

if __name__ == "__main__":
    logger.info("=== INICIANDO PROCESO TRADUCTOR LOCAL ===")

    # Identificador explícito de aplicación para la barra de tareas de Windows
    try:
        import ctypes
        myappid = "traductorlocal.offline.app.1"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QIcon(create_tray_icon_pixmap()))

    manager = None

    def on_activate():
        if manager:
            manager.activate_main_window()

    # Protección de Instancia Única
    if not ensure_single_instance(app, on_activate):
        logger.info("Ya había una instancia corriendo. Esta segunda instancia se cierra de inmediato.")
        sys.exit(0)

    manager = ApplicationManager(app)
    sys.exit(manager.start())
