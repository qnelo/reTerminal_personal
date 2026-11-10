#!/bin/bash
set -e

PORT="${1:-}"

if [ -z "$PORT" ]; then
    FOUND=$(ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || true)
    if [ -n "$FOUND" ]; then
        PORT=$(echo "$FOUND" | head -n 1)
    else
        echo "ERROR: Indica el puerto serie. Ej: $0 /dev/ttyUSB0"
        exit 1
    fi
fi

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TRMNL_DIR="$DIR/firmware/trmnl"

if [ ! -f "$TRMNL_DIR/firmware.bin" ]; then
    echo "ERROR: No se encontró $TRMNL_DIR/firmware.bin"
    exit 1
fi

echo "======================================================"
echo " Flasheando Firmware: TRMNL ePaper Dashboard 1.8.10"
echo " Puerto: $PORT"
echo "======================================================"

esptool --chip esp32s3 \
  -p "$PORT" \
  -b 921600 \
  --before default_reset \
  --after hard_reset \
  write_flash -z \
  --flash_mode dio \
  --flash_size 32MB \
  0x00000 "$TRMNL_DIR/bootloader.bin" \
  0x08000 "$TRMNL_DIR/partitions.bin" \
  0x0e000 "$TRMNL_DIR/boot_app0.bin" \
  0x10000 "$TRMNL_DIR/firmware.bin"

echo ""
echo "======================================================"
echo " Flasheo completado con éxito."
echo "======================================================"
