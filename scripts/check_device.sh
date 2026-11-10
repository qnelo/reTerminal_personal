#!/bin/bash
set -e

PORT="${1:-}"

# Priorizar esptool de .venv si existe
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -x "$DIR/.venv/bin/esptool" ]; then
    ESPTOOL="$DIR/.venv/bin/esptool"
else
    ESPTOOL="esptool"
fi

if [ -z "$PORT" ]; then
    FOUND=$(ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || true)
    if [ -n "$FOUND" ]; then
        PORT=$(echo "$FOUND" | head -n 1)
        echo "Puerto detectado automáticamente: $PORT"
    else
        echo "ERROR: No se detectó ningún puerto serie (/dev/ttyUSB* o /dev/ttyACM*)."
        echo "Asegúrate de:"
        echo " 1. Conectar el reTerminal E1002 con cable USB-C de datos."
        echo " 2. Encender el interruptor de encendido (Power Switch en ON)."
        echo " 3. Presionar el botón verde (KEY0) para despertarlo si está en Deep Sleep."
        echo ""
        echo "Uso: $0 [puerto]"
        exit 1
    fi
fi

echo "======================================================"
echo " Consultando información del ESP32-S3 en $PORT"
echo "======================================================"

"$ESPTOOL" --chip esp32s3 -p "$PORT" chip-id 2>/dev/null || "$ESPTOOL" --chip esp32s3 -p "$PORT" chip_id
echo ""
echo "Consultando detalles de la memoria Flash..."
"$ESPTOOL" --chip esp32s3 -p "$PORT" flash-id 2>/dev/null || "$ESPTOOL" --chip esp32s3 -p "$PORT" flash_id
echo ""
echo "Dispositivo conectado y listo para operar."
