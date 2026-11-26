"""
Monitor Global de Mouse y Captura de Texto Seleccionado para Windows.
Detecta selecciones con el ratón (arrastrar o doble clic) en cualquier ventana
y captura el texto de forma limpia mediante la API nativa de Windows,
restaurando el portapapeles previo del usuario y evitando disparos concurrentes.
"""

import time
import math
import ctypes
import ctypes.wintypes
import threading
import logging
from typing import Callable, Optional
from pynput import mouse
import pyperclip

logger = logging.getLogger("TraductorLocal.MouseMonitor")

# Constantes de la API de Windows
VK_CONTROL = 0x11
VK_C = 0x43
KEYEVENTF_KEYUP = 0x0002

user32 = ctypes.windll.user32


def simulate_ctrl_c():
    """Envía Ctrl+C de forma nativa a la ventana activa con códigos de escaneo de hardware."""
    scan_ctrl = user32.MapVirtualKeyW(VK_CONTROL, 0)
    scan_c = user32.MapVirtualKeyW(VK_C, 0)

    # 1. Presionar Ctrl
    user32.keybd_event(VK_CONTROL, scan_ctrl, 0, 0)
    time.sleep(0.02)

    # 2. Presionar C
    user32.keybd_event(VK_C, scan_c, 0, 0)
    time.sleep(0.02)

    # 3. Soltar C
    user32.keybd_event(VK_C, scan_c, KEYEVENTF_KEYUP, 0)
    time.sleep(0.02)

    # 4. Soltar Ctrl
    user32.keybd_event(VK_CONTROL, scan_ctrl, KEYEVENTF_KEYUP, 0)


def _is_window_chrome_drag(x: int, y: int) -> bool:
    """Detecta si el punto cae en la barra de título o scrollbar derecho de la ventana activa."""
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        rect = ctypes.wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False
        if rect.left <= x <= rect.right and rect.top <= y <= rect.bottom:
            if (y - rect.top) < 34:
                return True
            if (rect.right - x) < 24:
                return True
    except Exception:
        pass
    return False


class SelectionMonitor:
    def __init__(
        self,
        on_selection_detected: Callable[[str, int, int], None],
        on_click_outside: Optional[Callable[[int, int], None]] = None,
        drag_threshold_px: int = 6,
        settle_delay_ms: int = 90
    ):
        self.on_selection_detected = on_selection_detected
        self.on_click_outside = on_click_outside
        self.drag_threshold_px = drag_threshold_px
        self.settle_delay_sec = settle_delay_ms / 1000.0

        self.enabled = True
        self._listener: Optional[mouse.Listener] = None
        self._capture_lock = threading.Lock()

        self._press_x = 0
        self._press_y = 0
        self._press_time = 0.0

        self._last_click_time = 0.0
        self._last_click_x = 0
        self._last_click_y = 0

    def start(self):
        """Inicia el listener en un hilo de fondo."""
        if self._listener is None:
            self._listener = mouse.Listener(
                on_click=self._on_click
            )
            self._listener.daemon = True
            self._listener.start()
            logger.info("Monitor de ratón iniciado correctamente.")

    def stop(self):
        """Detiene el listener."""
        if self._listener:
            self._listener.stop()
            self._listener = None
            logger.info("Monitor de ratón detenido.")

    def _on_click(self, x: int, y: int, button: mouse.Button, pressed: bool):
        if not self.enabled:
            return

        # Si se pulsa cualquier botón secundario, notificar clic fuera
        if button != mouse.Button.left:
            if pressed and self.on_click_outside:
                self.on_click_outside(int(x), int(y))
            return

        now = time.time()

        if pressed:
            self._press_x = int(x)
            self._press_y = int(y)
            self._press_time = now

            if self.on_click_outside:
                self.on_click_outside(int(x), int(y))
        else:
            release_x = int(x)
            release_y = int(y)

            # Distancia de arrastre
            dist = math.hypot(release_x - self._press_x, release_y - self._press_y)
            is_drag = dist >= self.drag_threshold_px

            # Doble clic sobre una palabra
            time_diff = now - self._last_click_time
            pos_diff = math.hypot(release_x - self._last_click_x, release_y - self._last_click_y)
            is_double_click = (time_diff < 0.45) and (pos_diff < 10)

            self._last_click_time = now
            self._last_click_x = release_x
            self._last_click_y = release_y

            if is_drag or is_double_click:
                logger.debug(f"Gesto detectado (drag={is_drag}, dist={dist:.1f}px, double_click={is_double_click}) en ({release_x}, {release_y})")
                threading.Thread(
                    target=self._capture_selection_worker,
                    args=(release_x, release_y),
                    daemon=True
                ).start()

    def _capture_selection_worker(self, x: int, y: int):
        if not self._capture_lock.acquire(blocking=False):
            return

        try:
            # Filtrar arrastres sobre barra de título o scrollbar
            if _is_window_chrome_drag(x, y):
                logger.debug("Gesto ignorado por estar en barra de título o scrollbar.")
                return

            # 1. Espera pequeña para que la aplicación actualice el resaltado de selección
            time.sleep(self.settle_delay_sec)

            # 2. Número de secuencia del portapapeles de Windows antes de copiar
            seq_before = user32.GetClipboardSequenceNumber()

            # Guardar portapapeles previo
            prev_clipboard = ""
            try:
                prev_clipboard = pyperclip.paste()
            except Exception:
                pass

            # 3. Enviar Ctrl+C
            simulate_ctrl_c()

            # 4. Esperar de forma reactiva hasta 250ms a que la app actualice el portapapeles
            clipboard_changed = False
            for _ in range(25):
                time.sleep(0.01)
                if user32.GetClipboardSequenceNumber() != seq_before:
                    clipboard_changed = True
                    break

            # 5. Si no cambió el número de secuencia, esperar un breve momento extra
            if not clipboard_changed:
                time.sleep(0.06)

            # 6. Leer el contenido del portapapeles
            new_text = ""
            for _ in range(5):
                try:
                    new_text = pyperclip.paste()
                    break
                except Exception:
                    time.sleep(0.02)

            # 7. Restaurar el portapapeles original del usuario si cambió
            if clipboard_changed and prev_clipboard:
                time.sleep(0.02)
                try:
                    pyperclip.copy(prev_clipboard)
                except Exception:
                    pass

            if not new_text or not new_text.strip():
                logger.debug("No se capturó texto o la selección estaba vacía.")
                return

            clean_text = new_text.strip()

            # Si el texto es idéntico al previo y no cambió la secuencia, no hubo nueva selección
            if (clean_text == prev_clipboard.strip()) and not clipboard_changed:
                logger.debug("El texto es idéntico al que ya estaba copiado y no hubo copia nueva.")
                return

            logger.info(f"¡Texto seleccionado capturado con éxito! ({len(clean_text)} caracteres): {repr(clean_text[:40])}...")
            self.on_selection_detected(clean_text, x, y)
        finally:
            self._capture_lock.release()
