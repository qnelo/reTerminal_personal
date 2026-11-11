# Seeed Studio reTerminal E1002 - Repositorio de Documentación, Firmware y Proyectos

Repositorio centralizado con toda la información técnica, manuales, esquemáticos, binarios de firmware, ejemplos de ESPHome y proyectos listos para probar en el **Seeed Studio reTerminal E1002**.

---

## 📌 Enlaces Oficiales de Referencia

Este repositorio recopila y organiza el contenido de las siguientes fuentes oficiales:
1. **Página Oficial del Producto**: [Seeed Studio reTerminal E1002 (SKU 100017057)](https://www.seeedstudio.com/reTerminal-E1002-p-6533.html)
2. **Folleto y Especificaciones de la Pantalla (PDF)**: [reTerminal E Series ePaper Display PDF](https://files.seeedstudio.com/wiki/reterminal_e10xx/res/reTerminal_E_Series_ePaper_Display.pdf) *(Copia local en [docs/pdf/reTerminal_E_Series_ePaper_Display.pdf](docs/pdf/reTerminal_E_Series_ePaper_Display.pdf))*
3. **Esquemático Oficial V1.2 (PDF)**: [202004321_reTerminal_E1002_V1_2_SCH_251120.pdf](https://files.seeedstudio.com/wiki/reterminal_e10xx/res/202004321_reTerminal_E1002_V1_2_SCH_251120.pdf) *(Copia local en [docs/pdf/reTerminal_E1002_V1_2_SCH.pdf](docs/pdf/reTerminal_E1002_V1_2_SCH.pdf))*
4. **Wiki Oficial - Página Principal Serie reTerminal E**: [Seeed Studio Wiki - reTerminal E Series](https://wiki.seeedstudio.com/reterminal_e10xx_main_page/)
5. **Wiki Oficial - Primeros Pasos con E1002**: [Getting Started with reTerminal E1002](https://wiki.seeedstudio.com/getting_started_with_reterminal_e1002/)
6. **Wiki Oficial - Integración con ESPHome**: [reTerminal E Series with ESPHome](https://wiki.seeedstudio.com/reterminal_e10xx_with_esphome/)
7. **Web Firmware Hub & OSHW Repo**: [Firmware Flasher & YAML Generator](https://seeed-projects.github.io/OSHW-reTerminal-Series-E-D/)

---

## ⚡ Especificaciones Rápidas del Dispositivo

```
                  +----------------------------------------------+
                  |  [KEY0 / Verde]   [KEY1 / Blanco]  [KEY2]    |
                  +----------------------------------------------+
                  |                                              |
                  |                                              |
                  |         PANTALLA E INK SPECTRA 6             |
                  |                 7.3 PULGADAS                 |
                  |             800 x 480 FULL COLOR             |
                  |                                              |
                  |                                              |
                  +----------------------------------------------+
                  |  [LED Verde] [LED Rojo]     [USB-C] [SWITCH] |
                  +----------------------------------------------+
```

- **Microcontrolador**: Espressif ESP32-S3 (Dual-core Xtensa LX7 @ 240 MHz).
- **Memoria**: 8 MB PSRAM octal + 32 MB Flash SPI.
- **Pantalla**: 7.3" E Ink® Spectra™ 6 (6 colores saturados: Negro, Blanco, Rojo, Amarillo, Azul, Verde). Resolución: 800 × 480 px.
- **Batería**: Li-Po 2000 mAh integrada (~3 meses de autonomía con refrescos periódicos).
- **Sensores y Periféricos**:
  - Sensor de temperatura y humedad Sensirion SHT40 (I2C `0x44`).
  - Reloj de tiempo real RTC NXP PCF8563 (I2C `0x51`, soporte pila CR1220).
  - Lector de tarjeta MicroSD con pin de detección física y corte de energía.
  - Micrófono digital PDM con carril de apagado.
  - Zumbador piezoeléctrico (PWM).
  - Conector de expansión J2 de 8 pines (3.3V, GND, I2C, UART, ADC, GPIOs).

Consulta todos los detalles de diseño en [docs/HARDWARE.md](docs/HARDWARE.md).

---

## 🚀 Inicio Rápido y Uso Físico

1. **Encendido**: Mueve el interruptor físico trasero a la posición **ON**.
2. **Botón Verde (KEY0 - GPIO3)**:
   - **Pulsación corta**: Despierta el equipo si está en reposo / Forza el refresco manual de la pantalla.
   - **Pulsación larga (5 segundos)**: Con el firmware de fábrica, limpia toda la pantalla (evita sombras residuales si no lo vas a usar).
3. **Botones Blancos (KEY1 / GPIO4 y KEY2 / GPIO5)**:
   - Cambian entre páginas del dashboard (página anterior / siguiente).
   - **Pulsar ambos simultáneamente por 2 s**: Modo de reseteo de red Wi-Fi en el firmware de fábrica.
4. **LEDs**:
   - **Rojo**: Fijo = Cargando batería. Apagado = Carga completa o desconectado.
   - **Verde**: Indicador de estado de software.

---

## 🔄 Actualización y Flasheo de Firmware

El reTerminal se conecta a través del puente USB-a-UART CH340K por USB-C.

### 1. Comprobar Conexión
```bash
./scripts/check_device.sh
```

### 2. Respaldar la Memoria Flash Actual (Copia de Seguridad de 32 MB)
Antes de probar nuevos firmwares, haz una copia de seguridad:
```bash
./scripts/backup_flash.sh
```

### 3. Flashear Firmware de Fábrica (SenseCraft HMI v1.1.5)
Restaura el sistema original de Seeed Studio:
```bash
./scripts/flash_stock.sh
```

### 4. Flashear ESP32 PhotoFrame (Marco Digital Web a Color)
Transforma el reTerminal en un marco de fotos inteligente con servidor web autónomo:
```bash
./scripts/flash_photoframe.sh
```

### 5. Flashear TRMNL E-ink
Conéctalo a la plataforma de dashboards TRMNL:
```bash
./scripts/flash_trmnl.sh
```

Para instrucciones detalladas paso a paso, consulta [docs/FIRMWARE_GUIDE.md](docs/FIRMWARE_GUIDE.md).

---

## 🏠 Integración con ESPHome y Home Assistant

Este repositorio incluye configuraciones listas para usar en [esphome/](esphome/):

1. **Crea tu archivo de secretos**:
   ```bash
   cp esphome/secrets.yaml.example esphome/secrets.yaml
   # Edita tus credenciales de Wi-Fi y claves
   ```
2. **Dashboard Completo de 2 Páginas** ([esphome/reterminal_e1002_dashboard.yaml](esphome/reterminal_e1002_dashboard.yaml)):
   - Página 1: Temperatura y Humedad en tiempo real con sensor SHT40.
   - Página 2: Reloj de pared con sincronización Home Assistant.
   - Barra superior con porcentaje de batería y voltaje exacto.
   - Navegación interactiva con botones físicos y confirmación sonora en el zumbador.
3. **Prueba Mínima de Gráficos y Colores** ([esphome/reterminal_e1002_minimal.yaml](esphome/reterminal_e1002_minimal.yaml)).
4. **Diagnóstico Total de Periféricos** ([esphome/reterminal_e1002_all_peripherals.yaml](esphome/reterminal_e1002_all_peripherals.yaml)):
   - Display + SHT40 + RTC PCF8563 + Detección MicroSD + Micrófono PDM + Batería + Buzzer + LED.

Para compilar y flashear por cable:
```bash
esphome run esphome/reterminal_e1002_dashboard.yaml --device /dev/ttyUSB0
```

Consulta la guía completa de ESPHome en [docs/ESPHOME_GUIDE.md](docs/ESPHOME_GUIDE.md).

---

## 🌟 Proyectos Destacados

### 1. [Second Brain Display — Pendientes Simpli y Galería (reTerminal E1002)](projects/second_brain_display/README.md)
Visualizador de escritorio Always-On para los pendientes del segundo cerebro de SimpliRoute con modo alternativo de galería artística:
- **Modo Dual Interactivo**:
  - **Modo Pendientes Simpli**: 5 vistas navegables (Resumen con KPIs, Alta Prioridad, Media Prioridad, Baja Prioridad y Por Cliente).
  - **Modo Galería de Imágenes**: Infografías a pantalla completa (Árbol genealógico de *Cien años de soledad* sin spoilers, fotografías artísticas).
  - **Conmutación por Atajo Combo**: Presionar ambos botones blancos simultáneamente (`KEY1 + KEY2`) alterna de modo con doble tono de buzzer. El modo activo y la lámina elegida se guardan en memoria persistente (NVS), manteniéndose indefinidamente en pantalla hasta que se vuelva a pulsar la combinación.
- **Diseño Ultra-Legible para Spectra 6**: Tipografía bold pesada, tarjetas de alto contraste y cuantización optimizada a 16 colores (<64 KB).
- **Backend en Servidor / Raspberry Pi**: Servicio systemd sirviendo imágenes PNG y API JSON con telemetría en tiempo real (puerto :8088).
- **Firmware ESPHome Inteligente**:
  - Navegación por botones físicos frontales (Izquierdo: anterior, Derecho: siguiente, Verde: sincronizar).
  - Horario laboral inteligente (SNTP): refresco automático cada 15 min solo **Lunes a Viernes entre 08:45 y 19:00 hrs** (solo en Modo Pendientes).
  - Telemetría en pantalla: porcentaje de batería en cabecera y temperatura/humedad en pie de página.
  - Actualizaciones inalámbricas por Wi-Fi (**OTA**) con script inteligente de auto-detección de IP.

👉 [Ver documentación completa, capturas y arquitectura del proyecto](projects/second_brain_display/README.md).

---

## 📁 Estructura del Repositorio

```
.
├── README.md                              <- Este documento principal
├── .gitignore                             <- Exclusiones de Git
├── docs/                                  <- Documentación técnica y esquemáticos
│   ├── HARDWARE.md                        <- Pinout completo y diseño de hardware
│   ├── FIRMWARE_GUIDE.md                  <- Guía paso a paso de flasheo y recuperación
│   ├── ESPHOME_GUIDE.md                   <- Manual de componentes y configuración ESPHome
│   ├── LESSONS_LEARNED_OTA_AND_FIRMWARE.md<- Lecciones técnicas: buffer 64KB, chording y OTA
│   ├── LINKS_AND_RESOURCES.md             <- Enlaces consolidados a wikis, 3D y repos
│   └── pdf/                               <- Documentos PDF oficiales
│       ├── reTerminal_E_Series_ePaper_Display.pdf
│       └── reTerminal_E1002_V1_2_SCH.pdf
├── esphome/                               <- Configuraciones listas para Home Assistant
│   ├── reterminal_e1002_dashboard.yaml    <- Dashboard completo de 2 páginas con sensores
│   ├── reterminal_e1002_minimal.yaml      <- Test gráfico mínimo
│   ├── reterminal_e1002_all_peripherals.yaml <- Todos los periféricos (RTC, SD, Mic, etc.)
│   └── secrets.yaml.example               <- Plantilla de credenciales
├── firmware/                              <- Binarios de firmware listos para flashear
│   ├── stock/                             <- SenseCraft HMI 1.1.5 de fábrica
│   ├── photoframe/                        <- ESP32 PhotoFrame 2.18.0
│   └── trmnl/                             <- TRMNL 1.8.10
├── scripts/                               <- Scripts de automatización para Linux
│   ├── check_device.sh                    <- Detección e información del ESP32-S3
│   ├── backup_flash.sh                    <- Respaldo de los 32 MB de flash
│   ├── flash_stock.sh                     <- Flasheo de firmware de fábrica
│   ├── flash_photoframe.sh                <- Flasheo de ESP32 PhotoFrame
│   ├── flash_trmnl.sh                     <- Flasheo de TRMNL
│   ├── flash_ota.sh                       <- Flasheo OTA inalámbrico con auto-detección IP
│   └── erase_flash.sh                     <- Borrado completo de memoria
└── projects/                              <- Proyectos y desarrollos personalizados
    ├── README.md                          <- Banco de ideas y roadmap
    └── second_brain_display/              <- Visualizador de Pendientes del Second Brain
        ├── README.md                      <- Documentación, capturas y arquitectura
        ├── backend/                       <- Backend Python en la Raspberry Pi (API y Renderer)
        │   ├── data_provider.py           <- Conector con el Second Brain
        │   ├── renderer.py                <- Motor gráfico Pillow 800x480
        │   ├── generate_cien_anos_tree.py <- Generador del árbol genealógico
        │   ├── server.py                  <- Servidor HTTP, API y simulador web
        │   ├── gallery/                   <- Imágenes optimizadas de la galería (800x480)
        │   └── previews/                  <- Capturas de las vistas y galería generadas
        └── firmware/                      <- Firmware ESPHome para reTerminal E1002
            ├── second_brain_display.yaml  <- Configuración completa (Pantalla, Botones, SNTP, OTA)
            └── secrets.yaml.example       <- Plantilla de credenciales Wi-Fi
```
