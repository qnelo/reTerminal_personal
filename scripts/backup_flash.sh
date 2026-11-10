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

mkdir -p firmware/backup
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="firmware/backup/reterminal_e1002_full32MB_${TIMESTAMP}.bin"

echo "======================================================"
echo " Respaldando memoria Flash completa (32 MB) desde $PORT"
echo " Archivo de destino: $BACKUP_FILE"
echo " (Este proceso puede tardar entre 2 y 4 minutos)..."
echo "======================================================"

esptool --chip esp32s3 -p "$PORT" -b 921600 read_flash 0 0x2000000 "$BACKUP_FILE"

echo ""
echo "======================================================"
echo " Respaldo completado exitosamente: $BACKUP_FILE"
ls -lh "$BACKUP_FILE"
echo "======================================================"
