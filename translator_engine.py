"""
Motor de Traducción 100% Local y Offline (Inglés <-> Español).
Carga directa de modelos CTranslate2 (INT8) + SentencePiece/BPE desde disco
sin importar paquetes pesados (torch/stanza) en tiempo de ejecución.
"""

import os
import json
import threading
from pathlib import Path
from typing import Tuple, Optional, Callable, Dict, List
import ctranslate2
import sentencepiece as spm


class _FastSentencePieceTokenizer:
    """Tokenizador SentencePiece ligero sin dependencias externas."""
    def __init__(self, model_file: Path):
        self.processor = spm.SentencePieceProcessor(model_file=str(model_file))

    def encode(self, sentence: str) -> List[str]:
        return self.processor.encode(sentence, out_type=str)

    def decode(self, tokens: List[str]) -> str:
        return (
            self.processor.decode_pieces(tokens)
            .replace("▁", " ")
            .replace("_", " ")
        )


def _find_argos_model_dirs() -> Dict[Tuple[str, str], Path]:
    """Localiza directorios de paquetes Argos instalados directamente en disco."""
    search_roots = []
    local_app = os.environ.get("LOCALAPPDATA")
    app_data = os.environ.get("APPDATA")
    user_home = os.path.expanduser("~")

    if local_app:
        search_roots.append(Path(local_app) / "argos-translate" / "packages")
    search_roots.append(Path(user_home) / ".local" / "share" / "argos-translate" / "packages")
    if app_data:
        search_roots.append(Path(app_data) / "argos-translate" / "packages")

    found: Dict[Tuple[str, str], Path] = {}
    for root in search_roots:
        if not root.is_dir():
            continue
        for pkg_dir in root.iterdir():
            if not pkg_dir.is_dir():
                continue
            model_subdir = pkg_dir / "model"
            if not model_subdir.is_dir():
                continue

            from_code, to_code = None, None
            meta_file = pkg_dir / "metadata.json"
            if meta_file.is_file():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    from_code = meta.get("from_code")
                    to_code = meta.get("to_code")
                except Exception:
                    pass

            if not (from_code and to_code):
                name_lower = pkg_dir.name.lower()
                if "en_es" in name_lower:
                    from_code, to_code = "en", "es"
                elif "es_en" in name_lower:
                    from_code, to_code = "es", "en"

            if (from_code, to_code) in (("en", "es"), ("es", "en")):
                if (pkg_dir / "sentencepiece.model").is_file() or (pkg_dir / "bpe.model").is_file():
                    found[(from_code, to_code)] = pkg_dir
    return found


def _build_tokenizer_for_pkg_dir(pkg_dir: Path, from_code: str, to_code: str):
    sp_path = pkg_dir / "sentencepiece.model"
    if sp_path.is_file():
        return _FastSentencePieceTokenizer(sp_path)

    bpe_path = pkg_dir / "bpe.model"
    if bpe_path.is_file():
        from argostranslate.tokenizer import BPETokenizer
        return BPETokenizer(bpe_path, from_code, to_code)

    return None


class LocalTranslator:
    def __init__(self, on_status_changed: Optional[Callable[[str], None]] = None):
        self.on_status_changed = on_status_changed
        self.is_ready = False
        self.is_loading = False

        self._en_es_tokenizer = None
        self._en_es_translator = None

        self._es_en_tokenizer = None
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
                pkg_dirs = _find_argos_model_dirs()
                en_es_dir = pkg_dirs.get(("en", "es"))
                es_en_dir = pkg_dirs.get(("es", "en"))

                # Solo importar argostranslate.package si falta alguno en disco
                if not (en_es_dir and es_en_dir):
                    import argostranslate.package
                    self.update_status("Descargando modelos EN<->ES (solo la primera vez, ~80MB)...")
                    argostranslate.package.update_package_index()
                    available_packages = argostranslate.package.get_available_packages()

                    for pkg in available_packages:
                        if (pkg.from_code == "en" and pkg.to_code == "es" and not en_es_dir) or \
                           (pkg.from_code == "es" and pkg.to_code == "en" and not es_en_dir):
                            self.update_status(f"Instalando paquete local {pkg.from_code} -> {pkg.to_code}...")
                            download_path = pkg.download()
                            argostranslate.package.install_from_path(download_path)

                    pkg_dirs = _find_argos_model_dirs()
                    en_es_dir = pkg_dirs.get(("en", "es"))
                    es_en_dir = pkg_dirs.get(("es", "en"))

                if en_es_dir and es_en_dir:
                    self.update_status("Cargando traductores CTranslate2 en memoria...")
                    self._en_es_tokenizer = _build_tokenizer_for_pkg_dir(en_es_dir, "en", "es")
                    self._es_en_tokenizer = _build_tokenizer_for_pkg_dir(es_en_dir, "es", "en")

                    self._en_es_translator = ctranslate2.Translator(
                        str(en_es_dir / "model"),
                        device="cpu",
                        compute_type="default"
                    )
                    self._es_en_translator = ctranslate2.Translator(
                        str(es_en_dir / "model"),
                        device="cpu",
                        compute_type="default"
                    )

                    if self._en_es_tokenizer and self._es_en_tokenizer:
                        self.is_ready = True
                        self.is_loading = False
                        self.update_status("Modelos locales listos (100% Offline)")
                        if callback:
                            callback(True, "Modelos cargados correctamente")
                        return

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

        es_words = {
            "el", "la", "de", "que", "y", "a", "en", "un", "ser", "se", "no", "haber",
            "por", "con", "su", "para", "como", "estar", "tener", "le", "lo",
            "todo", "pero", "más", "mas", "hacer", "o", "poder", "este", "ya", "otro",
            "esta", "está", "estos", "estas", "del", "al", "los", "las", "una", "unos", "unas"
        }

        en_words = {
            "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it",
            "for", "not", "on", "with", "he", "as", "you", "do", "at", "this", "but",
            "his", "by", "from", "they", "we", "say", "her", "she", "or", "an",
            "will", "my", "one", "all", "would", "there", "their", "what", "so", "up", "out"
        }

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
        Traduce el texto localmente por lotes (batch) conservando saltos de línea.
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
                return "[Modelo no disponible aún. Estado: cargando...]", source_lang, target_lang

        try:
            if source_lang == "en":
                tokenizer = self._en_es_tokenizer
                translator = self._en_es_translator
            else:
                tokenizer = self._es_en_tokenizer
                translator = self._es_en_translator

            lines = clean_text.split("\n")
            non_empty_indices = []
            batch_tokens = []

            for idx, line in enumerate(lines):
                stripped = line.strip()
                if stripped:
                    non_empty_indices.append(idx)
                    batch_tokens.append(tokenizer.encode(stripped))

            translated_lines = [""] * len(lines)
            if batch_tokens:
                results = translator.translate_batch(batch_tokens, beam_size=2)
                for idx, res in zip(non_empty_indices, results):
                    hyp = res.hypotheses[0]
                    translated_lines[idx] = tokenizer.decode(hyp).strip()

            final_result = "\n".join(translated_lines)
            return final_result, source_lang, target_lang

        except Exception as e:
            return f"[Error al traducir: {str(e)}]", source_lang, target_lang
