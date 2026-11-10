#!/bin/bash
set -e

PORT="${1:-}"

if [ -z "$PORT" ]; then
    echo "Buscando puertos serie conectados..."
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

esptool --chip esp32s3 -p "$PORT" chip_id
echo ""
echo "Consultando detalles de la memoria Flash..."
esptool --chip esp32s3 -p "$PORT" flash_id
echo ""
echo "Dispositivo conectado y listo para flashear."
