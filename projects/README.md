# Banco de Proyectos para reTerminal E1002

Este directorio está diseñado para organizar y desarrollar los proyectos personalizados que iremos construyendo y probando en el **reTerminal E1002**.

---

## 💡 Ideas de Proyectos Listas para Implementar

### 1. Estación Meteorológica y Calidad de Aire de Escritorio
- **Tecnología**: ESPHome / Arduino
- **Funcionalidad**:
  - Lectura en tiempo real del sensor integrado **SHT40** (temperatura y humedad ambiental).
  - Consulta a la API de **Open-Meteo** o pronóstico de Home Assistant para pronóstico a 3 días y probabilidad de lluvia.
  - Alerta sonora suave con el zumbador y parpadeo de LED ante temperaturas extremas.
  - Gráficos históricos y diagramas a 6 colores en la pantalla Spectra 6.

### 2. Marco Digital de Fotografías Inteligente (ESP32 PhotoFrame)
- **Tecnología**: Firmware `ESP32 PhotoFrame` (disponible en `firmware/photoframe/`).
- **Funcionalidad**:
  - Servidor web embebido para arrastrar y soltar fotos desde el móvil o PC.
  - Algoritmo de difuminado (*Floyd-Steinberg dithering*) adaptado a la paleta exacta de 6 colores del panel Spectra 6.
  - Rotación automática de imágenes cada X horas o al pulsar el botón verde.

### 3. Tablero de Productividad Personal / Calendario Familiar
- **Tecnología**: ESPHome + Integración Google Calendar / CalDAV / Todoist.
- **Funcionalidad**:
  - Próximos eventos del día sincronizados desde el calendario.
  - Lista de tareas pendientes (ToDo list) con casillas de verificación.
  - Navegación entre vista de eventos y lista de tareas usando los botones físicos (KEY1 y KEY2).

### 4. Monitor de Criptomonedas / Finanzas / Métricas de Servidor
- **Tecnología**: ESPHome / HTTP Request / MQTT.
- **Funcionalidad**:
  - Seguimiento de precios (Bitcoin, Ethereum, divisas) o métricas de servidores locales (CPU, RAM, disco de tu Raspberry Pi).
  - Colores distintivos (Verde para subidas, Rojo para bajadas, Azul para neutro).

### 5. Grabadora de Notas de Voz con IA (Voice Memo to ePaper)
- **Tecnología**: Firmware AI Voice Memo / ESP-IDF con Groq API.
- **Funcionalidad**:
  - Mantener presionado el botón verde activa el micrófono PDM integrado.
  - El audio se envía a la API Whisper de Groq para transcripción instantánea y formateo en viñetas de tareas.
  - La pantalla ePaper se actualiza mostrando las tareas transcritas por IA.

---

## 🛠️ Estructura para Nuevos Proyectos

A medida que comencemos a crear proyectos, cada uno tendrá su propia subcarpeta:

```
projects/
├── 01_estacion_meteorologica/
│   ├── config.yaml
│   └── README.md
├── 02_calendario_familiar/
│   ├── ...
└── ...
```
