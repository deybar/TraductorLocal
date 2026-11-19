# 🌐 Traductor Local Offline (EN ➔ ES / ES ➔ EN) 🔒

> **Versión 1.0.0** — Traductor flotante 100% local, ultrarrápido y privado para Windows, inspirado en la interacción de selección con el ratón de QTranslate.

---

## 📌 ¿De qué se trata el proyecto y cuál es su propósito?

En muchas ocasiones trabajamos con textos, contratos, correos, documentación técnica o fragmentos de código confidenciales que **no deben ser enviados a servidores de terceros en internet** (como Google Translate o DeepL) por motivos de privacidad, seguridad o políticas corporativas.

Por otro lado, herramientas clásicas como **QTranslate** ofrecían la experiencia de usuario más ágil posible: **seleccionar un texto con el mouse en cualquier parte de la pantalla y ver aparecer un icono pequeño que al pulsarlo abre un popup flotante con la traducción**. Sin embargo, las herramientas tradicionales dependen de APIs en la nube o acumulan decenas de menús y opciones innecesarias.

**El propósito de este proyecto es resolver esa necesidad:**
1. **100% Local y Offline:** Todo el proceso de traducción neuronal ocurre íntegramente en tu propio ordenador (CPU local). **Ningún dato sale de tu equipo ni se conecta a internet.**
2. **Experiencia de Usuario Simple y Fluida:** Seleccionas texto en cualquier aplicación de Windows (Chrome, Word, PDFs, lectores de libros, etc.) y aparece un botón sutil cerca de tu cursor para traducir en un clic.
3. **Respuesta Instantánea:** Inferencia ultrarrápida (en menos de 50 milisegundos) gracias a modelos neuronales de pesos optimizados.

---

## ✨ Características Principales

- **🖱️ Captura Universal con el Ratón:** Detecta arrastres de selección o doble clic sobre cualquier palabra en cualquier ventana activa de Windows, sin ensuciar ni sobreescribir el contenido previo de tu portapapeles.
- **🔘 Icono Flotante Discreto (`文A`):** Pequeño botón compacto (26x26 px) con sombra suave que aparece cerca del cursor y se desvanece automáticamente a los pocos segundos si no se usa.
- **📏 Auto-ajuste Dinámico de Tamaño:** La ventana emergente (*popup*) calcula automáticamente su altura y anchura según la cantidad de caracteres, permitiéndote **leer párrafos completos de corrido sin tener que usar scroll**.
- **🖐️ Ventana Totalmente Arrastrable:** Puedes hacer clic y arrastrar la ventana flotante desde su barra superior (indicador `⠿`) para moverla libremente por la pantalla. Al moverla, se fija automáticamente (`📌`) para evitar cierres accidentales.
- **🎨 5 Temas Visuales:**
  - *Oscuro Clásico (Carbón)*: Negro profundo y minimalista.
  - *Oscuro Gris (Grafito / Slate)*: Tonos pizarra azulados sobrios.
  - *Oscuro Café (Moca Cálido)*: Tonos café cálidos con acentos ámbar.
  - *Oscuro Noche (Midnight)*: Azul marino oscuro de alto contraste.
  - *Claro Suave (Nord Minimal)*: Modo claro descansado para la vista.
- **🎚️ Control de Transparencia (Opacidad):** Deslizador regulable entre 70% y 100% para lograr un efecto traslúcido mientras lees.
- **🛡️ Protección de Instancia Única (Single Instance Guard):** Si el programa ya está corriendo, ejecutarlo nuevamente no duplica tareas ni iconos; simplemente restaura y enfoca la ventana existente.
- **🤫 Ejecución 100% Silenciosa:** Se inicia en segundo plano con cero ventanas negras de CMD estorbando en tu pantalla.

---

## 🛠️ Herramientas y Tecnologías Utilizadas

| Componente | Tecnología | Descripción |
|---|---|---|
| **Lenguaje** | Python 3.11+ | Lenguaje base del proyecto |
| **Interfaz de Usuario (GUI)** | PyQt6 (Qt 6) | Ventanas flotantes sin bordes, transparencias nativas y estilo CSS moderno |
| **Motor de Inferencia Neuronal** | CTranslate2 | Motor C++ de alto rendimiento optimizado para modelos Transformer en CPU |
| **Modelos de Lenguaje** | Argos Translate / OpenNMT | Modelos neuronales especializados en pares Inglés ↔ Español (~80 MB por modelo) |
| **Monitor Global de Ratón** | `pynput` | Captura global de eventos de ratón (clic, arrastre y coordenadas) |
| **Integración con Windows** | Win32 API (`ctypes`) | Consulta nativa de secuencias de portapapeles (`GetClipboardSequenceNumber`), simulación precisa de teclas con códigos de escaneo y AppUserModelID |
| **Gestión de Entorno** | `uv` / `pip` | Creación y administración ágil del entorno virtual de dependencias |

---

## 🚀 Cómo Ejecutar el Programa

### Opción 1: Ejecución Rápida (Para usuarios)
Simplemente haz doble clic en cualquiera de los lanzadores dentro de la carpeta del proyecto:
- **`iniciar.vbs`** *(Recomendado)*: Abre el traductor de forma **100% silenciosa** en segundo plano (sin ventana de consola CMD).
- **`iniciar.bat`**: Lanzador alternativo en archivo por lotes.
- **`debug_consola.bat`**: Abre la aplicación mostrando una ventana de consola en vivo con registros (*logs*) de depuración.

### Opción 2: Instalación y Ejecución desde Código Fuente (Para desarrolladores)
1. **Clonar o descargar el repositorio:**
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd 08_TraductorLocal
   ```

2. **Crear el entorno virtual con Python 3.11:**
   ```bash
   uv venv .venv --python 3.11
   # O con python estándar:
   # python -m venv .venv
   ```

3. **Instalar las dependencias:**
   ```bash
   uv pip install -r requirements.txt
   # O con pip estándar:
   # .venv\Scripts\pip install -r requirements.txt
   ```

4. **Ejecutar la aplicación:**
   ```bash
   .venv\Scripts\python.exe main.py
   ```

---

## 📂 Estructura del Código

```text
08_TraductorLocal/
├── main.py               # Orquestador principal, bandeja del sistema y Single Instance Guard
├── translator_engine.py  # Motor de traducción local CTranslate2 (EN <-> ES)
├── mouse_monitor.py      # Hook global de mouse y captura limpia de selección
├── floating_button.py    # Botón flotante miniatura (文A) con auto-ocultado
├── popup_window.py       # Ventana emergente con auto-ajuste de tamaño y arrastre
├── theme_config.py       # Paletas de 5 temas de color y persistencia en config.json
├── test_translation.py   # Script de consola para probar la traducción offline
├── test_mouse_capture.py # Script de diagnóstico para eventos de ratón
├── iniciar.vbs           # Lanzador 100% silencioso sin consola
├── iniciar.bat           # Lanzador rápido en batch
├── debug_consola.bat     # Lanzador con ventana de depuración visible
├── requirements.txt      # Lista de dependencias de Python
├── .gitignore            # Exclusión de temporales, caches y logs
└── README.md             # Esta documentación
```

---

## 🤝 Cómo Colaborar

¡Las contribuciones, sugerencias y mejoras son bienvenidas! Para colaborar:

1. **Reportar un error o proponer una idea:**
   - Abre un *Issue* describiendo el comportamiento esperado, los pasos para reproducirlo y el sistema operativo.
2. **Enviar mejoras de código:**
   - Realiza un *Fork* del repositorio.
   - Crea una rama para tu funcionalidad (`git checkout -b feature/nueva-mejora`).
   - Realiza tus cambios asegurándote de probar la traducción local con `python test_translation.py`.
   - Haz commit de tus cambios (`git commit -m "feat: descripción de la mejora"`).
   - Envía un *Pull Request* explicando la motivación del cambio.

---

## 📋 Hoja de Ruta y Documentación

- **[Documentación Técnica Completa](doc/README.md):** Arquitectura, flujo de procesamiento, protocolo IPC y guía de uso.
- **[Bitácora de Desarrollo y Roadmap](BITACORA.md):** Diagnóstico técnico, deudas priorizadas y registro de versiones.
- **[Integración en la Macro Suite de IA](doc/04_integracion_macro_sistema.md):** Relación con el Lanzador y las herramientas hermanas de audio y reuniones.

---

## 📄 Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Eres libre de usarlo, modificarlo y distribuirlo para fines personales o profesionales.
