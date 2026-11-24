#!/usr/bin/env python3
"""Self-check del refresco condicional (if_changed=1) y del render del dashboard de estadísticas.

Uso: .venv/bin/python projects/second_brain_display/backend/test_server_if_changed.py
"""
from __future__ import annotations

import copy
import datetime as dt
import http.client
import io
import threading
from http.server import ThreadingHTTPServer

from PIL import Image

import data_provider
import renderer
import server

# 1. Validar render con datos sintéticos y casos borde (0 pendientes, >7 clientes, valores altos)
def _sample_tab(total: int = 21, extra_clients: int = 0, scale: int = 1) -> dict:
    clientes = [
        {"nombre": "brightcell", "alta": 1 * scale, "media": 1 * scale, "baja": 3 * scale, "total": 5 * scale},
        {"nombre": "bat-brasil", "alta": 0, "media": 5 * scale, "baja": 0, "total": 5 * scale},
        {"nombre": "ada-copilot", "alta": 2 * scale, "media": 1 * scale, "baja": 0, "total": 3 * scale},
    ]
    for i in range(extra_clients):
        clientes.append({"nombre": f"cliente-{i+1}", "alta": 0, "media": 1, "baja": 0, "total": 1})
    hoy = dt.date(2026, 11, 24)
    serie = [
        {
            "dia": (hoy - dt.timedelta(days=13 - d)).isoformat(),
            "alta": (2 + d % 3) * scale,
            "media": (5 + d % 4) * scale,
            "baja": 4 * scale,
            "total": (11 + d % 3 + d % 4) * scale,
        }
        for d in range(14)
    ]
    return {
        "id": "estadistica",
        "tipo": "estadistica",
        "titulo": "Estadística",
        "hoy": hoy.isoformat(),
        "fecha_corta": "24-Nov",
        "total": total,
        "kpis": {
            "alta": {"n": 4 * scale, "prom": 3.8, "mediana": 3.0, "max": 8},
            "media": {"n": 11 * scale, "prom": 19.2, "mediana": 8, "max": 49},
            "baja": {"n": 6 * scale, "prom": 17.3, "mediana": 20.0, "max": 27},
        },
        "delta_ayer": -1,
        "delta_14d": 9,
        "por_cliente": clientes,
        "serie": serie,
    }


def _check_render(tab: dict, telemetry: dict | None = None) -> None:
    payload = {"hora_corta": "10:15", "fecha_corta": "24-Nov", "tabs": [tab]}
    img = renderer.render_view(0, payload, telemetry=telemetry)
    assert img.size == (800, 480) and img.mode == "RGB"
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    assert 1000 < len(buf.getvalue()) < 65536, f"PNG fuera de rango: {len(buf.getvalue())} bytes"


_check_render(_sample_tab(), telemetry={"vbat": 3.92, "temp": 25.6, "hum": 47.0})
_check_render(_sample_tab(total=0, scale=0) | {"por_cliente": [], "delta_ayer": 0, "delta_14d": 0})
_check_render(_sample_tab(total=30, extra_clients=8))  # activa colapso en OTROS (+K)
_check_render(_sample_tab(total=126, scale=6))         # valores > 100 y eje Y > 60

# 2. Validar exclusión de hibernados y consistencia real con el Second Brain
if data_provider.sb is not None and data_provider.estadistica is not None:
    hoy_test = dt.date(2026, 11, 24)
    synth = [
        data_provider.sb.Pendiente(
            slug="a1", titulo="Activo", descripcion="", prioridad="alta", estado="abierto",
            clase="", abierto=dt.date(2026, 11, 20), vence=None, resuelto=None,
            tags=["acme"], cliente="acme", secciones={},
        ),
        data_provider.sb.Pendiente(
            slug="h1", titulo="Hibernado", descripcion="", prioridad="baja", estado="hibernado",
            clase="", abierto=dt.date(2026, 11, 10), vence=None, resuelto=None,
            tags=["simplichat"], cliente="simplichat", secciones={}, hibernado=hoy_test,
        ),
    ]
    res_synth = data_provider.build_stats_payload(synth, [], {"acme"}, hoy_test)
    tab_synth = res_synth["tabs"][0]
    assert tab_synth["total"] == 1, "hibernado no debe sumar al total"
    assert tab_synth["kpis"]["baja"]["n"] == 0, "hibernado no debe sumar a su prioridad"
    assert [c["nombre"] for c in tab_synth["por_cliente"]] == ["acme"], "hibernado no debe aparecer en por_cliente"
    assert tab_synth["serie"][-1]["total"] == 1, "hibernado hoy no debe sumar en el día actual de la serie"

    live = data_provider.get_pendientes_data()
    assert live["total_vistas"] == 1
    t0 = live["tabs"][0]
    assert t0["tipo"] == "estadistica"
    assert sum(c["total"] for c in t0["por_cliente"]) == t0["total"], "suma por cliente == total"
    assert t0["serie"][-1]["total"] == t0["total"], "último día de la serie == total abiertos"
    assert len(t0["serie"]) == 14
    _check_render(t0, telemetry={"vbat": 4.0, "temp": 24.0, "hum": 50.0})

# 3. Validar refresco condicional HTTP 304 / 200 en server.py
DATA = {"hora_corta": "10:15", "fecha_corta": "24-Nov", "tabs": [_sample_tab()]}
server.LAST_DEVICE_HASH = None
server.get_pendientes_data = lambda: copy.deepcopy(DATA)
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
assert status(CHECK) == 304, "sin cambios en estadísticas responde 304"
assert status(DEVICE) == 200, "pedido forzado (botón, arranque) siempre dibuja"
assert status("mode=pendientes&idx=0") == 200 and status(CHECK) == 304, "el navegador no pisa el estado del reTerminal"

# Cambio en hora/telemetría NO debe disparar redibujado
DATA["hora_corta"] = "10:30"
assert status(CHECK) == 304, "el cambio de hora no debe invalidar el hash"

# Botones Izq/Der (idx=1, idx=-1) con 1 sola vista resuelven al mismo índice 0
assert status("mode=pendientes&idx=1&vbat=4.0&if_changed=1") == 304
assert status("mode=pendientes&idx=-1&vbat=4.0&if_changed=1") == 304

# Cambio en un conteo o en la serie SÍ debe disparar redibujado
DATA["tabs"][0]["total"] = 22
assert status(CHECK) == 200, "cambió el total de pendientes"
assert status(CHECK) == 304

DATA["tabs"][0]["serie"][-1]["alta"] += 1
assert status(CHECK) == 200, "cambió la serie de 14 días"
assert status(CHECK) == 304

assert status("mode=galeria&idx=0&vbat=4.0") == 200
assert status(CHECK) == 200, "volver de la galería siempre dibuja"

httpd.shutdown()
print("OK: dashboard de estadísticas, casos borde y refresco condicional")
