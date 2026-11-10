#!/usr/bin/env bash
# ==============================================================================
# flash_ota.sh
# Flashea firmware ESPHome vía Wi-Fi (OTA) al Seeed Studio reTerminal E1002.
# Detecta automáticamente la dirección IP del dispositivo o permite pasarla a mano.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ESPHOME_BIN="${ROOT_DIR}/.venv/bin/esphome"
DEFAULT_YAML="${ROOT_DIR}/projects/second_brain_display/firmware/second_brain_display.yaml"

# Colores de salida
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

TARGET_IP=""
YAML_FILE="${DEFAULT_YAML}"

# Parseo de argumentos
while [[ $# -gt 0 ]]; do
    case "$1" in
        --ip)
            TARGET_IP="$2"
            shift 2
            ;;
        --yaml)
            YAML_FILE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Uso: $0 [--ip <IP_DISPOSITIVO>] [--yaml <ARCHIVO_YAML>]"
            echo "Ejemplo: $0 --ip 192.168.4.87"
            exit 0
            ;;
        *)
            if [[ -z "${TARGET_IP}" && "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                TARGET_IP="$1"
            elif [[ -f "$1" ]]; then
                YAML_FILE="$1"
            fi
            shift
            ;;
    esac
done

echo -e "${BLUE}====================================================================${NC}"
echo -e "${BLUE}  reTerminal E1002 — Flasheo OTA (Over-The-Air) de Firmware       ${NC}"
echo -e "${BLUE}====================================================================${NC}"

# Validar binario de ESPHome
if [[ ! -x "${ESPHOME_BIN}" ]]; then
    echo -e "${RED}[ERROR] No se encontró el binario de ESPHome en ${ESPHOME_BIN}.${NC}"
    echo "Ejecuta: source .venv/bin/activate && pip install esphome"
    exit 1
fi

# Validar archivo YAML
if [[ ! -f "${YAML_FILE}" ]]; then
    echo -e "${RED}[ERROR] Archivo YAML no encontrado: ${YAML_FILE}${NC}"
    exit 1
fi

# Si no se pasó IP, intentar autodetección
if [[ -z "${TARGET_IP}" ]]; then
    echo -e "${YELLOW}[INFO] Buscando IP del reTerminal automáticamente...${NC}"

    # Método 1: Consultar la telemetría del servidor local si está corriendo
    DETECTED_IP=$(python3 -c "
import urllib.request, json
try:
    with urllib.request.urlopen('http://localhost:8088/api/gallery', timeout=1) as resp:
        data = json.loads(resp.read().decode())
        ip = data.get('telemetria', {}).get('client_ip')
        if ip: print(ip)
except Exception:
    pass
" 2>/dev/null || true)

    if [[ -n "${DETECTED_IP}" ]]; then
        TARGET_IP="${DETECTED_IP}"
        echo -e "${GREEN}[OK] IP detectada desde la telemetría del servidor backend: ${TARGET_IP}${NC}"
    else
        # Método 2: Resolver mDNS reterminal-second-brain.local
        echo -e "${YELLOW}[INFO] Probando resolución mDNS (reterminal-second-brain.local)...${NC}"
        MDNS_IP=$(python3 -c "
import socket
try:
    ip = socket.gethostbyname('reterminal-second-brain.local')
    print(ip)
except Exception:
    pass
" 2>/dev/null || true)

        if [[ -n "${MDNS_IP}" ]]; then
            TARGET_IP="${MDNS_IP}"
            echo -e "${GREEN}[OK] IP detectada vía mDNS: ${TARGET_IP}${NC}"
        fi
    fi
fi

# Si aún no tenemos IP, pedirla al usuario o intentar reterminal-second-brain.local
if [[ -z "${TARGET_IP}" ]]; then
    echo -e "${YELLOW}[AVISO] No se pudo detectar la IP de forma pasiva.${NC}"
    echo -e "Tip: Aprieta el botón verde (KEY0) en el reTerminal para que reporte su IP al backend."
    read -r -p "Ingresa la IP del reTerminal (o presiona Enter para usar reterminal-second-brain.local): " USER_IP
    if [[ -n "${USER_IP}" ]]; then
        TARGET_IP="${USER_IP}"
    else
        TARGET_IP="reterminal-second-brain.local"
    fi
fi

echo -e "\n${GREEN}Iniciando flasheo OTA hacia: ${TARGET_IP}${NC}"
echo -e "Archivo de configuración: ${YAML_FILE}\n"

exec "${ESPHOME_BIN}" run "${YAML_FILE}" --device "${TARGET_IP}"
