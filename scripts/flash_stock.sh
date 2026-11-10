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

STOCK_DIR="$DIR/firmware/stock"

if [ ! -f "$STOCK_DIR/firmware.bin" ]; then
    echo "ERROR: No se encontró $STOCK_DIR/firmware.bin"
    exit 1
fi

echo "======================================================"
echo " Flasheando Firmware de Fábrica: SenseCraft HMI 1.1.5"
echo " Puerto: $PORT"
echo " Velocidad: 921600 baudios"
echo "======================================================"

"$ESPTOOL" --chip esp32s3 \
  -p "$PORT" \
  -b 921600 \
  --before default_reset \
  --after hard_reset \
  write_flash -z \
  --flash_mode dio \
  --flash_freq 80m \
  --flash_size 32MB \
  0x00000 "$STOCK_DIR/bootloader.bin" \
  0x08000 "$STOCK_DIR/partitions.bin" \
  0x0e000 "$STOCK_DIR/boot_app0.bin" \
  0x90000 "$STOCK_DIR/firmware.bin"

echo ""
echo "======================================================"
echo " Flasheo completado con éxito."
echo " Reiniciando el dispositivo..."
echo "======================================================"
