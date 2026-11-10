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

echo "======================================================"
echo " ADVERTENCIA: Se borrará COMPLETAMENTE la memoria Flash"
echo " del ESP32-S3 en $PORT."
echo "======================================================"
read -p "¿Estás seguro de continuar? (s/N): " -r CONFIRM
if [[ ! "$CONFIRM" =~ ^[sSyY]$ ]]; then
    echo "Operación cancelada."
    exit 0
fi

echo "Borrando flash completa (32 MB)..."
esptool --chip esp32s3 -p "$PORT" erase_flash

echo ""
echo "Memoria Flash borrada con éxito."
