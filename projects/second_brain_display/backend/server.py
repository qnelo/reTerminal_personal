#!/usr/bin/env python3
"""
server.py
Servidor HTTP ligero para servir la API de datos y las imágenes renderizadas
del Second Brain al reTerminal E1002 y para previsualización web.
"""
from __future__ import annotations

import hashlib
import io
import ipaddress
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
from renderer import render_view, resolve_tab_index, voltage_to_percentage

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

PORT = int(os.environ.get("PORT", "8088"))
HOST = "0.0.0.0"

GLOBAL_TELEMETRY: dict[str, Any] = {
    "vbat": 4.11,
    "pct": 95,
    "temp": 26.6,
    "hum": 48.0,
    "client_ip": None,
    "updated_at": "2026-11-10 17:49:00",
}

# Hash de la última vista de pendientes enviada al reTerminal: con if_changed=1 y el mismo hash responde 304.
LAST_DEVICE_HASH: str | None = None

GALLERY_DIR = CURRENT_DIR / "gallery"


def get_gallery_images() -> list[Path]:
    GALLERY_DIR.mkdir(parents=True, exist_ok=True)
    images = sorted([p for p in GALLERY_DIR.glob("*.png")])
    if not images:
        try:
            from generate_cien_anos_tree import generate_tree_image
            target = GALLERY_DIR / "99_cien_anos_arbol.png"
            generate_tree_image(target)
            images = [target]
        except Exception as e:
            logging.error(f"Error auto-generando árbol genealógico: {e}")
    return images


def update_telemetry(params: dict, client_ip: str | None = None):
    updated = False
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # La IP que el reTerminal reporta de sí mismo gana a la de origen: detrás de un router con NAT
    # la de origen es la del router y el OTA no llega.
    ip = params.get("ip", [client_ip])[0]
    if ip and "vbat" in params:  # solo el reTerminal manda vbat: un curl o navegador no pisa su IP de OTA
        try:
            GLOBAL_TELEMETRY["client_ip"] = str(ipaddress.ip_address(ip))  # termina como argumento de esphome
            updated = True
        except ValueError:
            pass
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
        elif path in ("/api/gallery", "/api/galeria"):
            self.send_gallery_json()
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
            update_telemetry(params, self.client_address[0])
            data = get_pendientes_data()
            data["telemetria"] = GLOBAL_TELEMETRY
            tabs = data.get("tabs", [])
            if "idx" in params and tabs:
                try:
                    idx = int(params["idx"][0])
                except (ValueError, TypeError):
                    idx = 0
                payload = dict(tabs[resolve_tab_index(idx, tabs)])
                payload["telemetria"] = GLOBAL_TELEMETRY
            elif "view" in params and tabs:
                view = params["view"][0]
                matched = next((t for t in tabs if t.get("id") == view), None)
                if matched:
                    payload = dict(matched)
                    payload["telemetria"] = GLOBAL_TELEMETRY
                else:
                    payload = data
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

    def send_gallery_json(self):
        try:
            images = get_gallery_images()
            payload = {
                "total": len(images),
                "images": [p.name for p in images],
                "telemetria": GLOBAL_TELEMETRY,
            }
            resp_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(resp_bytes)
        except Exception as e:
            logging.error(f"Error generando JSON de galería: {e}")
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))

    def send_image_response(self, params: dict):
        global LAST_DEVICE_HASH
        try:
            update_telemetry(params, self.client_address[0])
            mode = params.get("mode", ["pendientes"])[0].lower()

            # Modo Galería de Imágenes
            if mode in ("galeria", "gallery"):
                images = get_gallery_images()
                if not images:
                    self.send_error(HTTPStatus.NOT_FOUND, "No hay imágenes en la galería")
                    return
                try:
                    idx = int(params.get("idx", ["0"])[0])
                except (ValueError, TypeError):
                    idx = 0
                idx = idx % len(images)
                target_img_path = images[idx]
                if "vbat" in params:  # la pantalla ya no muestra pendientes: el próximo pedido debe dibujar
                    LAST_DEVICE_HASH = None
                with open(target_img_path, "rb") as f:
                    img_bytes = f.read()

                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(img_bytes)))
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.end_headers()
                self.wfile.write(img_bytes)
                return

            # Modo Pendientes de Simpli (pestañas dinámicas: Resumen + 1 por cliente)
            data = get_pendientes_data()
            tabs = data.get("tabs", [])
            if "idx" in params:
                try:
                    raw_idx = int(params["idx"][0])
                except (ValueError, TypeError):
                    raw_idx = 0
                resolved_idx = resolve_tab_index(raw_idx, tabs)
            else:
                view = params.get("view", ["resumen"])[0]
                resolved_idx = resolve_tab_index(view, tabs)

            tab_payload = tabs[resolved_idx] if tabs else None
            # Solo el contenido de la pestaña y el total de pestañas [k/N]: hora y telemetría no cuentan.
            view_json = json.dumps([resolved_idx, len(tabs), tab_payload], sort_keys=True, ensure_ascii=False)
            view_hash = hashlib.sha256(view_json.encode("utf-8")).hexdigest()
            if "if_changed" in params and view_hash == LAST_DEVICE_HASH:
                self.send_response(HTTPStatus.NOT_MODIFIED)
                self.end_headers()
                return

            img = render_view(resolved_idx, data, telemetry=GLOBAL_TELEMETRY)

            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            img_bytes = buf.getvalue()

            if "vbat" in params:  # solo el reTerminal manda vbat: la vista previa del navegador no pisa el estado
                LAST_DEVICE_HASH = view_hash
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
    
    <div class="nav" id="navBar">
        <a class="btn active" href="#" onclick="loadTab(0, this); return false;">[1/1] Resumen</a>
        <a class="btn" href="/api/pendientes" target="_blank">Ver JSON API 🔗</a>
    </div>

    <div class="preview-box">
        <img id="previewImg" src="/render?mode=pendientes&idx=0" alt="Vista E-Ink" width="800" height="480">
    </div>

    <div class="info-panel">
        <p>• <strong>Endpoint de Pendientes</strong>: <code>http://&lt;IP_DE_LA_PI&gt;:8088/render?mode=pendientes&amp;idx=0</code></p>
        <p>• <strong>Endpoint de Galería</strong>: <code>http://&lt;IP_DE_LA_PI&gt;:8088/render?mode=galeria&amp;idx=0</code></p>
        <p>• <strong>Atajo de Botones en reTerminal</strong>: Presionar <strong>Izquierdo + Derecho juntos</strong> conmuta entre Pendientes y Galería.</p>
    </div>

    <script>
        function setActive(el) {
            document.querySelectorAll('.btn').forEach(b => b.classList.remove('active'));
            if (el) el.classList.add('active');
        }
        function loadTab(idx, el) {
            setActive(el);
            document.getElementById('previewImg').src = '/render?mode=pendientes&idx=' + idx + '&t=' + Date.now();
        }
        function loadGallery(idx, el) {
            setActive(el);
            document.getElementById('previewImg').src = '/render?mode=galeria&idx=' + idx + '&t=' + Date.now();
        }
        async function buildNav() {
            const nav = document.getElementById('navBar');
            const [pRes, gRes] = await Promise.all([fetch('/api/pendientes'), fetch('/api/gallery')]);
            const pData = await pRes.json();
            const gData = await gRes.json();
            const tabs = pData.tabs || [];
            const imgs = gData.images || [];
            nav.innerHTML = '';
            tabs.forEach((t, i) => {
                const a = document.createElement('a');
                a.className = 'btn' + (i === 0 ? ' active' : '');
                a.href = '#';
                const label = t.tipo === 'resumen' ? `[${i + 1}/${tabs.length}] Resumen` : `[${i + 1}/${tabs.length}] ${t.cliente} (${t.total})`;
                a.textContent = label;
                a.onclick = (ev) => { ev.preventDefault(); loadTab(i, a); };
                nav.appendChild(a);
            });
            imgs.forEach((name, i) => {
                const a = document.createElement('a');
                a.className = 'btn';
                a.style.borderColor = '#f59e0b';
                a.style.color = '#fbbf24';
                a.href = '#';
                a.textContent = `🖼️ [Galería ${i + 1}/${imgs.length}] ${name}`;
                a.onclick = (ev) => { ev.preventDefault(); loadGallery(i, a); };
                nav.appendChild(a);
            });
            const apiBtn = document.createElement('a');
            apiBtn.className = 'btn';
            apiBtn.href = '/api/pendientes';
            apiBtn.target = '_blank';
            apiBtn.textContent = 'Ver JSON API 🔗';
            nav.appendChild(apiBtn);
        }
        buildNav();
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
        msg = "%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args)
        logging.info(msg)
        sys.stdout.flush()


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
