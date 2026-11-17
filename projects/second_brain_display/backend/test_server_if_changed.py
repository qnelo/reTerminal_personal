#!/usr/bin/env python3
"""Self-check del refresco condicional: /render?if_changed=1 responde 304 solo si la pestaña que el reTerminal
tiene en pantalla no cambió (incluyendo cambios en la cantidad total de pestañas).

Uso: .venv/bin/python projects/second_brain_display/backend/test_server_if_changed.py
"""

import http.client
import threading
from http.server import ThreadingHTTPServer

from PIL import Image

import server

DATA = {
    "tabs": [
        {"id": "resumen", "tipo": "resumen", "titulo": "Resumen", "total": 3},
        {"id": "cliente:bat", "tipo": "cliente", "titulo": "BAT", "total": 2},
    ]
}
server.get_pendientes_data = lambda: DATA
server.render_view = lambda view, data, telemetry=None: Image.new("RGB", (8, 8))

httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()


def status(query: str) -> int:
    conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1])
    conn.request("GET", "/render?" + query)
    resp = conn.getresponse()
    resp.read()
    conn.close()
    return resp.status


DEVICE = "mode=pendientes&idx=0&vbat=4.0"
CHECK = DEVICE + "&if_changed=1"

assert status(CHECK) == 200, "sin estado previo (servidor recién arrancado) siempre dibuja"
assert status(CHECK) == 304, "misma pestaña sin cambios"
assert status(DEVICE) == 200, "pedido forzado (botón, arranque) siempre dibuja"
assert status("mode=pendientes&idx=0") == 200 and status(CHECK) == 304, "el navegador no pisa el estado del reTerminal"

DATA["tabs"][0]["total"] = 4
assert status(CHECK) == 200, "cambió la pestaña en pantalla"
assert status(CHECK) == 304

DATA["tabs"][1]["total"] = 5  # cambio en otra pestaña: no es la que está en pantalla
assert status(CHECK) == 304

# Cambio en el número total de pestañas sí debe redibujar aunque el contenido de resumen sea igual (cambia [1/N])
DATA["tabs"].append({"id": "cliente:manantial", "tipo": "cliente", "titulo": "MANANTIAL", "total": 1})
assert status(CHECK) == 200, "cambió el total de pestañas [1/N]"
assert status(CHECK) == 304

# Índice negativo envuelve al último cliente (manantial)
assert status("mode=pendientes&idx=-1&vbat=4.0&if_changed=1") == 200, "índice negativo envuelve al último cliente"
assert status("mode=pendientes&idx=2&vbat=4.0&if_changed=1") == 304, "idx=2 equivale a idx=-1 con 3 pestañas"

assert status("mode=galeria&idx=0&vbat=4.0") == 200
assert status(CHECK) == 200, "volver de la galería siempre dibuja"

httpd.shutdown()
print("OK: refresco condicional y pestañas dinámicas")
