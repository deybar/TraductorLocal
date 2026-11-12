"""
Script de prueba para verificar el motor de traducción local offline en consola.
"""

from translator_engine import LocalTranslator

def main():
    print("=" * 60)
    print("  PRUEBA DEL MOTOR DE TRADUCCIÓN LOCAL OFFLINE")
    print("=" * 60)

    def on_status(msg):
        print(f"[*] {msg}")

    translator = LocalTranslator(on_status_changed=on_status)
    print("\nInicializando modelos locales (Inglés <-> Español)...")
    translator._load_or_install_models()

    if not translator.is_ready:
        print("[!] Error: No se pudieron cargar los modelos.")
        return

    print("\n[OK] Modelos listos. Probando traducciones:\n")

    # Prueba 1: Inglés a Español
    text_en = "Hello world! This is a completely local and offline translation test."
    translated_es, src, dst = translator.translate(text_en)
    print(f"Original ({src.upper()}): {text_en}")
    print(f"Traducción ({dst.upper()}): {translated_es}\n")

    # Prueba 2: Español a Inglés
    text_es = "Esta es una prueba de traducción del español al inglés sin conexión a internet."
    translated_en, src, dst = translator.translate(text_es)
    print(f"Original ({src.upper()}): {text_es}")
    print(f"Traducción ({dst.upper()}): {translated_en}\n")

    print("=" * 60)
    print("  PRUEBA COMPLETADA CON ÉXITO")
    print("=" * 60)

if __name__ == "__main__":
    main()
