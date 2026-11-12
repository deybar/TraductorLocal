"""
Diagnóstico de eventos de ratón y selección de texto en vivo.
"""
import time
import math
import ctypes
from pynput import mouse
import pyperclip

VK_CONTROL = 0x11
VK_C = 0x43
KEYEVENTF_KEYUP = 0x0002

def simulate_ctrl_c():
    user32 = ctypes.windll.user32
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_C, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_C, 0, KEYEVENTF_KEYUP, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

press_x = 0
press_y = 0
press_time = 0

def on_click(x, y, button, pressed):
    global press_x, press_y, press_time
    if button != mouse.Button.left:
        return
    if pressed:
        press_x = x
        press_y = y
        press_time = time.time()
        print(f"[MOUSE] Click presionado en ({x}, {y})")
    else:
        dist = math.hypot(x - press_x, y - press_y)
        dt = time.time() - press_time
        print(f"[MOUSE] Click soltado en ({x}, {y}) - Distancia: {dist:.1f}px, Tiempo: {dt:.2f}s")
        if dist > 6 or dt > 0.4:
            print("  -> Detectado arrastre o pulsación. Intentando capturar selección...")
            time.sleep(0.1)
            prev = ""
            try:
                prev = pyperclip.paste()
            except Exception as e:
                print(f"  -> Error al leer prev: {e}")
            simulate_ctrl_c()
            time.sleep(0.1)
            new_text = ""
            try:
                new_text = pyperclip.paste()
            except Exception as e:
                print(f"  -> Error al leer new: {e}")
            print(f"  -> Texto capturado: {repr(new_text)}")

print("Iniciando listener de prueba. Arrastra el ratón sobre cualquier texto...")
listener = mouse.Listener(on_click=on_click)
listener.start()
time.sleep(15)
listener.stop()
print("Fin de la prueba.")
