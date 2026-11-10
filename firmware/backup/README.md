# Respaldo de Fábrica de la Memoria Flash

En esta carpeta se almacena la copia de seguridad completa (32 MB) del chip ESP32-S3 del **reTerminal E1002**, tomada el 10 de noviembre de 2026 antes de cualquier modificación.

## Archivo de Respaldo Comprimido
- **Archivo**: `reterminal_e1002_full32MB_20261110_115716.bin.gz` (Comprimido con gzip: ~1.1 MB).
- **Tamaño descomprimido**: 33,554,432 bytes (32 MB).

## Cómo Descomprimir
```bash
gunzip -k reterminal_e1002_full32MB_20261110_115716.bin.gz
```

## Cómo Restaurar en el reTerminal E1002
```bash
.venv/bin/esptool --chip esp32s3 -p /dev/ttyUSB0 -b 921600 write_flash 0x0 firmware/backup/reterminal_e1002_full32MB_20261110_115716.bin
```
