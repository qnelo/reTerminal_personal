#!/usr/bin/env python3
"""
server.py
Servidor HTTP ligero para servir la API de datos y las imágenes renderizadas
del Second Brain al reTerminal E1002 y para previsualización web.
"""
from __future__ import annotations

import io
import json
import logging
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Agregar directorio actual al path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from datetime import datetime
from typing import Any

from data_provider import get_pendientes_data
from renderer import render_view, voltage_to_percentage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PORT = int(os.environ.get("PORT", "8088"))
HOST = "0.0.0.0"

GLOBAL_TELEMETRY: dict[str, Any] = {
    "vbat": 4.11,
    "pct": 95,
    "temp": 26.6,
    "hum": 48.0,
    "updated_at": "2026-11-10 17:49:00",
}


def update_telemetry(params: dict):
    updated = False
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if "vbat" in params:
        try:
            v = float(params["vbat"][0])
            GLOBAL_TELEMETRY["vbat"] = v
            GLOBAL_TELEMETRY["pct"] = voltage_to_percentage(v)
            updated = True
        except (ValueError, TypeError):
            pass
    if "temp" in params:
        try:
            GLOBAL_TELEMETRY["temp"] = float(params["temp"][0])
            updated = True
        except (ValueError, TypeError):
            pass
    if "hum" in params:
        try:
            GLOBAL_TELEMETRY["hum"] = float(params["hum"][0])
            updated = True
        except (ValueError, TypeError):
            pass
    if updated:
        GLOBAL_TELEMETRY["updated_at"] = now_str


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path in ("/api/pendientes", "/api/data"):
            self.send_json_response(params)
        elif path == "/render":
            self.send_image_response(params)
        elif path.startswith("/previews/"):
            self.send_static_preview(path)
        elif path == "/health":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "service": "second_brain_display"}')
        elif path == "/" or path == "/index.html":
            self.send_html_dashboard()
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Ruta no encontrada")

    def send_json_response(self, params: dict):
        try:
            update_telemetry(params)
            data = get_pendientes_data()
            data["telemetria"] = GLOBAL_TELEMETRY
            view = params.get("view", [None])[0]
            if view and view in data.get("vistas", {}):
                payload = data["vistas"][view]
                payload["telemetria"] = GLOBAL_TELEMETRY
            else:
                payload = data

            resp_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(resp_bytes)
        except Exception as e:
            logging.error(f"Error generando JSON: {e}")
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))

    def send_image_response(self, params: dict):
        try:
            view = params.get("view", ["resumen"])[0]
            update_telemetry(params)
            data = get_pendientes_data()
            img = render_view(view, data, telemetry=GLOBAL_TELEMETRY)

            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            img_bytes = buf.getvalue()

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(img_bytes)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(img_bytes)
        except Exception as e:
            logging.error(f"Error renderizando imagen: {e}")
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))

    def send_static_preview(self, path: str):
        fname = Path(path).name
        file_path = CURRENT_DIR / "previews" / fname
        if file_path.exists() and file_path.suffix == ".png":
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Imagen no encontrada")

    def send_html_dashboard(self):
        html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>reTerminal E1002 - Pendientes Simpli</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 24px; }
        h1 { color: #38bdf8; margin-bottom: 8px; }
        .subtitle { color: #94a3b8; margin-bottom: 24px; }
        .nav { display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }
        .btn { background: #1e293b; color: #f8fafc; border: 1px solid #334155; padding: 10px 18px; border-radius: 6px; text-decoration: none; font-weight: bold; cursor: pointer; transition: all 0.2s; }
        .btn:hover, .btn.active { background: #0284c7; border-color: #38bdf8; }
        .preview-box { background: #000; border: 2px solid #334155; border-radius: 10px; padding: 12px; display: inline-block; max-width: 100%; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); }
        img { display: block; max-width: 100%; height: auto; border-radius: 4px; }
        .info-panel { margin-top: 24px; font-size: 14px; color: #94a3b8; }
        code { background: #1e293b; padding: 2px 6px; border-radius: 4px; color: #38bdf8; }
    </style>
</head>
<body>
    <h1>📟 reTerminal E1002 — Pendientes Simpli</h1>
    <div class="subtitle">Simulador y API en vivo del panel de pendientes para la pantalla E Ink Spectra 6 (800×480)</div>
    
    <div class="nav">
        <a class="btn active" href="#" onclick="loadView('resumen', this)">[1/5] Resumen</a>
        <a class="btn" href="#" onclick="loadView('alta', this)">[2/5] Alta Prioridad</a>
        <a class="btn" href="#" onclick="loadView('media', this)">[3/5] Media Prioridad</a>
        <a class="btn" href="#" onclick="loadView('baja', this)">[4/5] Baja Prioridad</a>
        <a class="btn" href="#" onclick="loadView('clientes', this)">[5/5] Por Cliente</a>
        <a class="btn" href="/api/pendientes" target="_blank">Ver JSON API 🔗</a>
    </div>

    <div class="preview-box">
        <img id="previewImg" src="/render?view=resumen" alt="Vista E-Ink" width="800" height="480">
    </div>

    <div class="info-panel">
        <p>• <strong>Endpoint de Imagen para reTerminal</strong>: <code>http://&lt;IP_DE_LA_PI&gt;:8088/render?view=resumen</code></p>
        <p>• <strong>Endpoint de JSON</strong>: <code>http://&lt;IP_DE_LA_PI&gt;:8088/api/pendientes</code></p>
    </div>

    <script>
        function loadView(view, el) {
            document.querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
            if (el) el.classList.add('active');
            const img = document.getElementById('previewImg');
            img.src = '/render?view=' + view + '&t=' + Date.now();
        }
    </script>
</body>
</html>"""
        resp_bytes = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.end_headers()
        self.wfile.write(resp_bytes)

    def log_message(self, format, *args):
        logging.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))


def run_server():
    server_address = (HOST, PORT)
    httpd = ThreadingHTTPServer(server_address, Handler)
    logging.info(f"🚀 Servidor Second Brain Display iniciado en http://{HOST}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        logging.info("Servidor detenido.")


if __name__ == "__main__":
    run_server()
