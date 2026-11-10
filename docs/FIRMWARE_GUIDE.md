# Guía Completa de Actualización y Flasheo de Firmware

Esta guía describe cómo respaldar, actualizar y flashear diferentes firmwares en el **reTerminal E1002** desde Linux (por ejemplo desde tu Raspberry Pi u ordenador), macOS o Windows.

---

## 1. Ecosistemas de Firmware Disponibles

El reTerminal E1002 admite múltiples entornos de software según el proyecto que desees construir:

| Firmware | Tipo | Caso de Uso Principal |
| :--- | :--- | :--- |
| **SenseCraft Seeedash (Stock)** | No-Code Cloud | Dashboards visuales desde el navegador, galería de widgets comunitarios, plantillas prediseñadas. |
| **ESPHome** | Local / Open Source | Integración nativa total con **Home Assistant**, control de pantalla mediante YAML, sensores locales (SHT40, batería, botones). |
| **ESP32 PhotoFrame** | Standalone / Web UI | Marco digital fotográfico a todo color con servidor web local para subir fotos, rotación automática y API REST. |
| **TRMNL E-ink** | Plataforma Dashboard | Integración con la plataforma de dashboards web TRMNL (funciona en modo monocromático en E1002). |
| **Arduino / PlatformIO / ESP-IDF** | Desarrollo a medida | Programación en C/C++ usando librerías como `GxEPD2`, `Seeed_GFX`, `LVGL` o ESP-IDF v5.x nativo. |

---

## 2. Requisitos Previos y Conexión USB

1. **Cable USB-C de datos**: Asegúrate de usar un cable con líneas de datos completas (no un cable que solo cargue batería).
2. **Interruptor de Encendido (Power Switch)**: El interruptor en la parte trasera del dispositivo **DEBE estar en la posición ON**. Si el interruptor está en OFF, el ESP32-S3 no recibe energía para comunicarse por USB.
3. **Controlador USB-a-UART (CH340K)**:
   - En **Linux / Raspberry Pi OS**: El controlador `ch341` viene integrado en el kernel. Al conectar el dispositivo aparecerá como `/dev/ttyUSB0` (o `/dev/ttyACM0`).
   - En **macOS**: Puede requerir el driver WCH CH340 (`/dev/tty.wchusbserial*`).
   - En **Windows**: Aparecerá como puerto `COMx` (usualmente COM3, COM4, etc.).
4. **Verificación en Linux**:
   ```bash
   # Comprobar si el dispositivo es reconocido
   ls -la /dev/ttyUSB* /dev/ttyACM*
   dmesg | grep -i ch341
   ```

---

## 3. Poner el Dispositivo en Modo Bootloader (Descarga)

El reTerminal E1002 incluye circuito auto-reset (DTR/RTS) que normalmente entra en modo bootloader automáticamente al ejecutar `esptool`.

Si por alguna razón el microcontrolador no responde o está en modo Deep Sleep:
1. Asegúrate de que el switch de encendido esté en **ON**.
2. Presiona una vez el **botón verde (KEY0)** para despertar al procesador del reposo.
3. Si aún así no entra en modo bootloader, mantén presionado el **botón blanco izquierdo (KEY1 / GPIO4)** o el **botón verde (KEY0)** mientras conectas el cable USB o apagas y vuelves a encender el switch.

---

## 4. Respaldar la Memoria Flash Actual (Copia de Seguridad)

Antes de cambiar de firmware, es una buena práctica respaldar la memoria Flash completa de 32 MB para poder volver exactamente al estado de fábrica en cualquier momento:

```bash
# Crear directorio de respaldo
mkdir -p firmware/backup

# Ejecutar el script incluido en este repositorio:
./scripts/backup_flash.sh /dev/ttyUSB0

# O ejecutar esptool directamente:
esptool --chip esp32s3 -p /dev/ttyUSB0 -b 921600 read_flash 0 0x2000000 firmware/backup/backup_full_32MB.bin
```
*(Nota: La lectura de los 32 MB tomará entre 2 y 4 minutos).*

---

## 5. Restaurar el Firmware de Fábrica (SenseCraft HMI v1.1.5)

El firmware original de Seeed Studio viene incluido en la carpeta `firmware/stock/`.

### Opción A: Usando el script del repositorio
```bash
chmod +x scripts/*.sh
./scripts/flash_stock.sh /dev/ttyUSB0
```

### Opción B: Comando manual con esptool
```bash
esptool --chip esp32s3 \
  -p /dev/ttyUSB0 \
  -b 921600 \
  --before default_reset \
  --after hard_reset \
  write_flash -z \
  --flash_mode dio \
  --flash_freq 80m \
  --flash_size 32MB \
  0x00000 firmware/stock/bootloader.bin \
  0x08000 firmware/stock/partitions.bin \
  0x0e000 firmware/stock/boot_app0.bin \
  0x90000 firmware/stock/firmware.bin
```

---

## 6. Flashear ESP32 PhotoFrame (Marco de Fotos Web)

El firmware **ESP32 PhotoFrame** convierte el reTerminal E1002 en un marco de fotos inteligente con servidor web autónomo y algoritmo de difuminado (dithering) optimizado para la pantalla Spectra 6:

```bash
# Con el script del repo:
./scripts/flash_photoframe.sh /dev/ttyUSB0

# O manualmente:
esptool --chip esp32s3 \
  -p /dev/ttyUSB0 \
  -b 921600 \
  write_flash -z \
  --flash_mode dio \
  --flash_size 32MB \
  0x0 firmware/photoframe/photoframe_e1002_merged_2.18.0.bin
```

**Primeros pasos con PhotoFrame:**
1. Al reiniciar, el dispositivo creará una red Wi-Fi de configuración (punto de acceso).
2. Conéctate a dicha red desde tu teléfono u ordenador para configurar tu Wi-Fi doméstico.
3. Una vez conectado, accede a la IP asignada mediante tu navegador web para subir fotos a todo color en resolución 800×480.

---

## 7. Flashear TRMNL E-ink Dashboard

Para vincular el dispositivo con la plataforma de dashboards TRMNL:

```bash
# Con el script del repo:
./scripts/flash_trmnl.sh /dev/ttyUSB0

# O manualmente:
esptool --chip esp32s3 \
  -p /dev/ttyUSB0 \
  -b 921600 \
  write_flash -z \
  --flash_mode dio \
  --flash_size 32MB \
  0x00000 firmware/trmnl/bootloader.bin \
  0x08000 firmware/trmnl/partitions.bin \
  0x0e000 firmware/trmnl/boot_app0.bin \
  0x10000 firmware/trmnl/firmware.bin
```

---

## 8. Compilar y Flashear con ESPHome

Para utilizar el reTerminal con **Home Assistant** o como dispositivo autónomo con ESPHome:

1. Instala ESPHome en tu entorno:
   ```bash
   pip install esphome
   ```
2. Edita `esphome/secrets.yaml` (creado a partir de `secrets.yaml.example`) con tus credenciales de Wi-Fi.
3. Compila y flashea el archivo YAML:
   ```bash
   # Flasheo inicial por cable USB:
   esphome run esphome/reterminal_e1002_dashboard.yaml --device /dev/ttyUSB0
   
   # Actualizaciones posteriores por Wi-Fi (OTA):
   esphome run esphome/reterminal_e1002_dashboard.yaml
   ```

---

## 9. Flasheo Directo desde el Navegador Web (Web Flasher)

Si prefieres flashear sin usar la terminal de comandos, puedes usar Chrome o Edge en tu PC/Mac:
- **Firmware Hub Oficial OSHW Seeed**: [https://seeed-projects.github.io/OSHW-reTerminal-Series-E-D/](https://seeed-projects.github.io/OSHW-reTerminal-Series-E-D/)
  - Selecciona `reTerminal E1002`.
  - Elige el firmware deseado (SenseCraft HMI, PhotoFrame, TRMNL, demos de periféricos).
  - Haz clic en **Flash** y selecciona el puerto serie en la ventana del navegador.
- **SenseCraft HMI Flasher**: [https://sensecraft.seeed.cc/hmi](https://sensecraft.seeed.cc/hmi)

---

## 10. Limpieza Completa de Flash (Erase Flash)

Cuando cambies entre firmwares con tablas de particiones incompatibles (por ejemplo de SenseCraft a PhotoFrame o ESPHome), se recomienda borrar la memoria Flash para evitar que fragmentos del sistema de archivos NVS anterior interfieran:

```bash
./scripts/erase_flash.sh /dev/ttyUSB0
# O con esptool:
esptool --chip esp32s3 -p /dev/ttyUSB0 erase_flash
```
