#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PIDFILE="$DIR/projects/second_brain_display/backend/server.pid"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo "Servidor con PID $PID detenido."
    else
        echo "El servidor con PID $PID no estaba en ejecución."
    fi
    rm -f "$PIDFILE"
else
    echo "No hay archivo PID. El servidor no está corriendo."
fi
