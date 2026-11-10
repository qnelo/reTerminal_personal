#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PYTHON="$DIR/.venv/bin/python"
PIDFILE="$DIR/projects/second_brain_display/backend/server.pid"

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "El servidor ya está corriendo con PID $(cat "$PIDFILE")"
    exit 0
fi

nohup "$PYTHON" -u "$DIR/projects/second_brain_display/backend/server.py" > "$DIR/projects/second_brain_display/backend/server.log" 2>&1 &
echo $! > "$PIDFILE"
echo "Servidor Second Brain Display iniciado con PID $(cat "$PIDFILE") en el puerto 8088"
