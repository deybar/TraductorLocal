# 📡 02. Protocolo IPC y Configuración

Este documento detalla el mecanismo de comunicación entre procesos (IPC), control de instancia única y persistencia de configuración de **Traductor Local Offline**.

---

## 1. Control de Instancia Única vía Named Pipes de Qt

Para evitar la apertura accidental de múltiples instancias en segundo plano que compitan por los hooks del ratón de Windows, el programa implementa un servidor de sockets locales (`QLocalServer`):

- **Nombre del Socket:** `TraductorLocal_SingleInstance_2026`
- **Comportamiento en Inicio:**
  1. El script crea un `QLocalSocket` e intenta conectarse a `TraductorLocal_SingleInstance_2026`.
  2. Si la conexión tiene éxito:
     - Envía el comando en bytes `b"ACTIVATE"`.
     - La instancia que ya estaba abierta recibe la señal, se desenfoca de la bandeja del sistema, restaura su ventana y se trae al frente (`raise_()`, `activateWindow()`).
     - La nueva ejecución se cierra limpiamente con código de salida `0`.
  3. Si la conexión falla:
     - Asume que es la instancia maestra.
     - Remueve posibles sockets huérfanos anteriores (`QLocalServer.removeServer(...)`).
     - Abre la escucha del socket y registra el callback de activación.

---

## 2. Archivo de Configuración (`config.json`)

Los parámetros de personalización se persisten en formato JSON estándar en la raíz del proyecto:

```json
{
  "theme": "Oscuro Café (Moca Cálido)",
  "opacity": 95,
  "icon_size": 24,
  "font_size": 13
}
```

### Campos Soportados:
| Campo | Tipo | Valores Posibles | Descripción |
|---|---|---|---|
| `theme` | string | Nombre del tema | Estilo de color (Carbón, Grafito, Moca, Midnight, Nord). |
| `opacity` | integer | `70` a `100` | Nivel de opacidad porcentual de la ventana emergente. |
| `icon_size` | integer | `20` a `36` | Tamaño en píxeles del botón flotante `文A`. |
| `font_size` | integer | `11` a `18` | Tamaño en puntos tipográficos del texto en el popup. |
