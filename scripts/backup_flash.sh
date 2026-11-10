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

mkdir -p "$DIR/firmware/backup"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$DIR/firmware/backup/reterminal_e1002_full32MB_${TIMESTAMP}.bin"

echo "======================================================"
echo " Respaldando memoria Flash completa (32 MB) desde $PORT"
echo " Archivo de destino: $BACKUP_FILE"
echo " Herramienta: $ESPTOOL"
echo " (Este proceso puede tardar entre 2 y 4 minutos)..."
echo "======================================================"

"$ESPTOOL" --chip esp32s3 -p "$PORT" -b 921600 read-flash 0 0x2000000 "$BACKUP_FILE" 2>/dev/null || \
"$ESPTOOL" --chip esp32s3 -p "$PORT" -b 921600 read_flash 0 0x2000000 "$BACKUP_FILE"

echo ""
echo "======================================================"
echo " Respaldo completado exitosamente: $BACKUP_FILE"
ls -lh "$BACKUP_FILE"
echo "======================================================"
