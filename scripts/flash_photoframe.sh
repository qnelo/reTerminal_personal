#!/bin/bash
set -e

PORT="${1:-}"

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
    else
        echo "ERROR: Indica el puerto serie. Ej: $0 /dev/ttyUSB0"
        exit 1
    fi
fi

BIN="$DIR/firmware/photoframe/photoframe_e1002_merged_2.18.0.bin"

if [ ! -f "$BIN" ]; then
    echo "ERROR: No se encontró $BIN"
    exit 1
fi

echo "======================================================"
echo " Flasheando Firmware: ESP32 PhotoFrame 2.18.0"
echo " Puerto: $PORT"
echo " (Imagen completa unificada en offset 0x0)"
echo "======================================================"

"$ESPTOOL" --chip esp32s3 \
  -p "$PORT" \
  -b 921600 \
  --before default_reset \
  --after hard_reset \
  write_flash -z \
  --flash_mode dio \
  --flash_size 32MB \
  0x0 "$BIN"

echo ""
echo "======================================================"
echo " Flasheo completado."
echo " Conéctate a la red Wi-Fi que emitirá el reTerminal"
echo " para configurar tu red y acceder a la interfaz web."
echo "======================================================"
