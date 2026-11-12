"""
Gestor de Temas y Configuración Visual (Temas, Opacidad y Estilos).
"""

import os
import json
import logging

logger = logging.getLogger("TraductorLocal.ThemeConfig")

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

THEMES = {
    "Oscuro Clásico (Carbón)": {
        "bg": "#18181b",
        "card_bg": "#121214",
        "input_bg": "#09090b",
        "border": "#27272a",
        "border_focus": "#52525b",
        "text_primary": "#f4f4f5",
        "text_secondary": "#a1a1aa",
        "badge_bg": "#3f3f46",
        "badge_text": "#f4f4f5",
        "btn_bg": "#27272a",
        "btn_hover": "#3f3f46",
        "btn_text": "#e4e4e7",
        "icon_bg": "#27272a",
        "icon_border": "#3f3f46",
        "icon_hover": "#3f3f46",
        "icon_text": "#f4f4f5"
    },
    "Oscuro Gris (Grafito / Slate)": {
        "bg": "#1e222a",
        "card_bg": "#242933",
        "input_bg": "#1b1e25",
        "border": "#3b4252",
        "border_focus": "#81a1c1",
        "text_primary": "#eceff4",
        "text_secondary": "#94a3b8",
        "badge_bg": "#434c5e",
        "badge_text": "#eceff4",
        "btn_bg": "#2e3440",
        "btn_hover": "#3b4252",
        "btn_text": "#eceff4",
        "icon_bg": "#2e3440",
        "icon_border": "#434c5e",
        "icon_hover": "#3b4252",
        "icon_text": "#eceff4"
    },
    "Oscuro Café (Moca Cálido)": {
        "bg": "#1c1614",
        "card_bg": "#241c19",
        "input_bg": "#171210",
        "border": "#3d2f2b",
        "border_focus": "#785348",
        "text_primary": "#f5f5f4",
        "text_secondary": "#d6c7b2",
        "badge_bg": "#44342e",
        "badge_text": "#fed7aa",
        "btn_bg": "#2e2320",
        "btn_hover": "#3d2f2b",
        "btn_text": "#fed7aa",
        "icon_bg": "#2a201d",
        "icon_border": "#4a3832",
        "icon_hover": "#3d2f2b",
        "icon_text": "#f5f5f4"
    },
    "Oscuro Noche (Midnight Azul)": {
        "bg": "#0a0f1d",
        "card_bg": "#0f172a",
        "input_bg": "#070b14",
        "border": "#1e293b",
        "border_focus": "#38bdf8",
        "text_primary": "#f8fafc",
        "text_secondary": "#94a3b8",
        "badge_bg": "#1e293b",
        "badge_text": "#38bdf8",
        "btn_bg": "#1e293b",
        "btn_hover": "#334155",
        "btn_text": "#e2e8f0",
        "icon_bg": "#1e293b",
        "icon_border": "#334155",
        "icon_hover": "#334155",
        "icon_text": "#f8fafc"
    },
    "Claro Suave (Nord Minimal)": {
        "bg": "#f1f5f9",
        "card_bg": "#ffffff",
        "input_bg": "#f8fafc",
        "border": "#cbd5e1",
        "border_focus": "#64748b",
        "text_primary": "#0f172a",
        "text_secondary": "#64748b",
        "badge_bg": "#e2e8f0",
        "badge_text": "#1e293b",
        "btn_bg": "#e2e8f0",
        "btn_hover": "#cbd5e1",
        "btn_text": "#0f172a",
        "icon_bg": "#f8fafc",
        "icon_border": "#cbd5e1",
        "icon_hover": "#e2e8f0",
        "icon_text": "#1e293b"
    }
}

DEFAULT_CONFIG = {
    "theme": "Oscuro Clásico (Carbón)",
    "opacity": 94,
    "icon_size": 26
}

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(data)
                return config
        except Exception as e:
            logger.warning(f"Error al leer config.json: {e}")
    return DEFAULT_CONFIG.copy()

def save_config(cfg: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Error al guardar config.json: {e}")

def get_theme_data(theme_name: str) -> dict:
    return THEMES.get(theme_name, THEMES["Oscuro Clásico (Carbón)"])
