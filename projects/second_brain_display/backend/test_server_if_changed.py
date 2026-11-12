#!/usr/bin/env python3
"""Self-check del refresco condicional: /render?if_changed=1 responde 304 solo si la vista que el reTerminal
tiene en pantalla no cambió.

Uso: .venv/bin/python projects/second_brain_display/backend/test_server_if_changed.py
"""

import http.client
import threading
from http.server import ThreadingHTTPServer

from PIL import Image

import server

DATA = {"vistas": {"resumen": {"total_abiertos": 3}, "alta": {"total": 1}}}
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


DEVICE = "view=resumen&vbat=4.0"
CHECK = DEVICE + "&if_changed=1"

assert status(CHECK) == 200, "sin estado previo (servidor recién arrancado) siempre dibuja"
assert status(CHECK) == 304, "misma vista sin cambios"
assert status(DEVICE) == 200, "pedido forzado (botón, arranque) siempre dibuja"
assert status("view=resumen") == 200 and status(CHECK) == 304, "el navegador no pisa el estado del reTerminal"

DATA["vistas"]["resumen"]["total_abiertos"] = 4
assert status(CHECK) == 200, "cambió la vista en pantalla"
assert status(CHECK) == 304

DATA["vistas"]["alta"]["total"] = 2  # cambio en otra vista: no es la que está en pantalla
assert status(CHECK) == 304

assert status("view=alta&vbat=4.0&if_changed=1") == 200, "otra vista en pantalla dibuja"
assert status("mode=galeria&idx=0&vbat=4.0") == 200
assert status(CHECK) == 200, "volver de la galería siempre dibuja"

httpd.shutdown()
print("OK: refresco condicional")
