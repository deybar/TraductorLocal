"""
Motor de Traducción 100% Local y Offline (Inglés <-> Español).
Utiliza modelos neuronales locales (Argos Translate / CTranslate2) sin enviar ningún dato a internet.
Garantiza privacidad total en el equipo local con traducción ultrarrápida (en milisegundos).
"""

import threading
from typing import Tuple, Optional, Callable
import ctranslate2
import argostranslate.package

class LocalTranslator:
    def __init__(self, on_status_changed: Optional[Callable[[str], None]] = None):
        self.on_status_changed = on_status_changed
        self.is_ready = False
        self.is_loading = False

        self._en_es_pkg = None
        self._en_es_translator = None

        self._es_en_pkg = None
        self._es_en_translator = None

        self._lock = threading.Lock()

    def update_status(self, msg: str):
        if self.on_status_changed:
            self.on_status_changed(msg)

    def initialize_models_async(self, callback: Optional[Callable[[bool, str], None]] = None):
        """Inicializa los modelos en segundo plano para no congelar la interfaz."""
        thread = threading.Thread(target=self._load_or_install_models, args=(callback,), daemon=True)
        thread.start()

    def _load_or_install_models(self, callback: Optional[Callable[[bool, str], None]] = None):
        with self._lock:
            if self.is_ready:
                if callback:
                    callback(True, "Modelos ya listos")
                return

            self.is_loading = True
            try:
                self.update_status("Verificando modelos locales...")
                installed_packages = argostranslate.package.get_installed_packages()

                self._en_es_pkg = next((p for p in installed_packages if p.from_code == "en" and p.to_code == "es"), None)
                self._es_en_pkg = next((p for p in installed_packages if p.from_code == "es" and p.to_code == "en"), None)

                # Si falta algún modelo, se descarga e instala localmente una única vez
                if not (self._en_es_pkg and self._es_en_pkg):
                    self.update_status("Descargando modelos EN<->ES (solo la primera vez, ~80MB)...")
                    argostranslate.package.update_package_index()
                    available_packages = argostranslate.package.get_available_packages()

                    for pkg in available_packages:
                        if (pkg.from_code == "en" and pkg.to_code == "es" and not self._en_es_pkg) or \
                           (pkg.from_code == "es" and pkg.to_code == "en" and not self._es_en_pkg):
                            self.update_status(f"Instalando paquete local {pkg.from_code} -> {pkg.to_code}...")
                            download_path = pkg.download()
                            argostranslate.package.install_from_path(download_path)

                    # Recargar paquetes instalados
                    installed_packages = argostranslate.package.get_installed_packages()
                    self._en_es_pkg = next((p for p in installed_packages if p.from_code == "en" and p.to_code == "es"), None)
                    self._es_en_pkg = next((p for p in installed_packages if p.from_code == "es" and p.to_code == "en"), None)

                if self._en_es_pkg and self._es_en_pkg:
                    self.update_status("Cargando traductores CTranslate2 en memoria...")
                    self._en_es_translator = ctranslate2.Translator(str(self._en_es_pkg.package_path / "model"))
                    self._es_en_translator = ctranslate2.Translator(str(self._es_en_pkg.package_path / "model"))

                    self.is_ready = True
                    self.is_loading = False
                    self.update_status("Modelos locales listos (100% Offline)")
                    if callback:
                        callback(True, "Modelos cargados correctamente")
                else:
                    self.is_ready = False
                    self.is_loading = False
                    err = "No se pudieron inicializar los idiomas locales EN/ES."
                    self.update_status(err)
                    if callback:
                        callback(False, err)

            except Exception as e:
                self.is_ready = False
                self.is_loading = False
                err = f"Error al cargar modelos: {str(e)}"
                self.update_status(err)
                if callback:
                    callback(False, err)

    def detect_language(self, text: str) -> str:
        """
        Detección rápida y ligera entre Español e Inglés sin depender de internet.
        Utiliza frecuencias de caracteres y palabras clave comunes.
        """
        text_lower = text.lower()
        words = set("".join(c if c.isalnum() else " " for c in text_lower).split())

        # Palabras ultra frecuentes en español
        es_words = {
            "el", "la", "de", "que", "y", "a", "en", "un", "ser", "se", "no", "haber",
            "por", "con", "su", "para", "como", "estar", "tener", "le", "lo",
            "todo", "pero", "más", "mas", "hacer", "o", "poder", "este", "ya", "otro",
            "esta", "está", "estos", "estas", "del", "al", "los", "las", "una", "unos", "unas"
        }

        # Palabras ultra frecuentes en inglés
        en_words = {
            "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it",
            "for", "not", "on", "with", "he", "as", "you", "do", "at", "this", "but",
            "his", "by", "from", "they", "we", "say", "her", "she", "or", "an",
            "will", "my", "one", "all", "would", "there", "their", "what", "so", "up", "out"
        }

        # Caracteres específicos del español
        spanish_chars = set("áéíóúüñ¿¡")
        if any(c in text_lower for c in spanish_chars):
            return "es"

        es_count = sum(1 for w in words if w in es_words)
        en_count = sum(1 for w in words if w in en_words)

        if es_count > en_count:
            return "es"
        elif en_count > es_count:
            return "en"

        return "en"

    def translate(self, text: str, force_source: Optional[str] = None) -> Tuple[str, str, str]:
        """
        Traduce el texto localmente.
        Retorna: (texto_traducido, idioma_origen, idioma_destino)
        """
        if not text or not text.strip():
            return "", "en", "es"

        clean_text = text.strip()
        source_lang = force_source if force_source in ("en", "es") else self.detect_language(clean_text)
        target_lang = "es" if source_lang == "en" else "en"

        if not self.is_ready:
            self._load_or_install_models()
            if not self.is_ready:
                return f"[Modelo no disponible aún. Estado: cargando...]", source_lang, target_lang

        try:
            if source_lang == "en":
                pkg = self._en_es_pkg
                translator = self._en_es_translator
            else:
                pkg = self._es_en_pkg
                translator = self._es_en_translator

            # Dividir por líneas para conservar saltos de párrafo
            lines = clean_text.split("\n")
            translated_lines = []

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    translated_lines.append("")
                    continue

                # Tokenizar con el tokenizador del paquete
                tokens = pkg.tokenizer.encode(stripped)
                # Traducir con el motor CTranslate2 local
                result = translator.translate_batch([tokens])
                hyp = result[0].hypotheses[0]
                # Decodificar de vuelta a texto limpio
                translated_text = pkg.tokenizer.decode(hyp)
                translated_lines.append(translated_text)

            final_result = "\n".join(translated_lines)
            return final_result, source_lang, target_lang

        except Exception as e:
            return f"[Error al traducir: {str(e)}]", source_lang, target_lang
