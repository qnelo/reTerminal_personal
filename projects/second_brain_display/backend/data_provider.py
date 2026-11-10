"""
data_provider.py
Consume datos del Second Brain (simpli-second-brain) usando herramientas del ecosistema
y los estructura en modelos limpios listos para visualización en el reTerminal E1002.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

# Intentar importar sb desde el path estándar del bundle
SB_TOOLS = Path(os.environ.get("SB_TOOLS") or "/home/pi/develop/personal/simpli-second-brain/tools/herdr-pendientes")
if str(SB_TOOLS) not in sys.path:
    sys.path.insert(0, str(SB_TOOLS))

try:
    import sb
except ImportError:
    sb = None


def format_due_date(vence: dt.date | None, today: dt.date) -> str:
    if not vence:
        return ""
    diff = (vence - today).days
    day_str = vence.strftime("%d-%b")
    if diff == 0:
        return f"{day_str} (Hoy)"
    elif diff == 1:
        return f"{day_str} (Mañana)"
    elif diff < 0:
        return f"{day_str} ({diff}d atraso)"
    else:
        return f"{day_str} (+{diff}d)"


def get_priority_color(prioridad: str) -> str:
    """Devuelve código de color semántico para la pantalla Spectra 6"""
    if prioridad in ("muy-alta", "alta"):
        return "RED"
    elif prioridad in ("media-alta", "media"):
        return "YELLOW"
    elif prioridad == "baja":
        return "GREEN"
    return "BLACK"


def get_pendientes_data() -> dict[str, Any]:
    if sb is None:
        return {"error": "Módulo sb.py no encontrado en " + str(SB_TOOLS)}

    today = dt.date.today()
    pendientes, proyectos = sb.cargar()

    # Filtrar solo los abiertos
    abiertos = [p for p in pendientes if p.estado == "abierto"]

    # Ordenar por prioridad
    prio_order = {"muy-alta": 0, "alta": 1, "media-alta": 2, "media": 3, "baja": 4}
    abiertos.sort(key=lambda p: (prio_order.get(p.prioridad, 99), p.vence or dt.date(2099, 1, 1)))

    # Contadores
    conteo_alta = len([p for p in abiertos if p.prioridad in ("muy-alta", "alta")])
    conteo_media = len([p for p in abiertos if p.prioridad in ("media-alta", "media")])
    conteo_baja = len([p for p in abiertos if p.prioridad == "baja"])

    cli_counter = Counter([p.cliente.upper() for p in abiertos])
    top_clientes = [{"cliente": c, "count": cnt} for c, cnt in cli_counter.most_common(5)]

    def to_card(p, index: int = 1) -> dict[str, Any]:
        due_str = format_due_date(p.vence, today)
        return {
            "index": index,
            "slug": p.slug,
            "titulo": p.titulo,
            "cliente": p.cliente.upper(),
            "prioridad": p.prioridad,
            "color": get_priority_color(p.prioridad),
            "vence_str": due_str,
            "es_urgente": p.prioridad in ("muy-alta", "alta") or (p.vence and (p.vence - today).days <= 1),
        }

    # Vista 0: Resumen General
    top_urgentes = [to_card(p, i + 1) for i, p in enumerate(abiertos[:4])]
    vista_resumen = {
        "titulo": "Resumen General",
        "total_abiertos": len(abiertos),
        "kpis": {
            "alta": conteo_alta,
            "media": conteo_media,
            "baja": conteo_baja,
        },
        "top_urgentes": top_urgentes,
        "top_clientes": top_clientes,
    }

    # Vista 1: Alta Prioridad
    items_alta = [to_card(p, i + 1) for i, p in enumerate([p for p in abiertos if p.prioridad in ("muy-alta", "alta")])]
    vista_alta = {
        "titulo": "Prioridad Alta",
        "total": len(items_alta),
        "color": "RED",
        "items": items_alta[:5],  # Primeros 5 para legibilidad máxima
    }

    # Vista 2: Media Prioridad
    items_media = [to_card(p, i + 1) for i, p in enumerate([p for p in abiertos if p.prioridad in ("media-alta", "media")])]
    vista_media = {
        "titulo": "Prioridad Media",
        "total": len(items_media),
        "color": "YELLOW",
        "items": items_media[:5],
    }

    # Vista 3: Baja Prioridad
    items_baja = [to_card(p, i + 1) for i, p in enumerate([p for p in abiertos if p.prioridad == "baja"])]
    vista_baja = {
        "titulo": "Prioridad Baja",
        "total": len(items_baja),
        "color": "GREEN",
        "items": items_baja[:5],
    }

    # Vista 4: Por Clientes
    grupos_cliente = []
    for cliente_name, cnt in cli_counter.most_common(4):
        cli_tasks = [to_card(p) for p in abiertos if p.cliente.upper() == cliente_name][:2]
        grupos_cliente.append({
            "cliente": cliente_name,
            "conteo": cnt,
            "tareas": cli_tasks,
        })

    vista_clientes = {
        "titulo": "Por Cliente",
        "total_clientes": len(cli_counter),
        "grupos": grupos_cliente,
    }

    return {
        "timestamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hora_corta": dt.datetime.now().strftime("%H:%M"),
        "total_abiertos": len(abiertos),
        "vistas": {
            "resumen": vista_resumen,
            "alta": vista_alta,
            "media": vista_media,
            "baja": vista_baja,
            "clientes": vista_clientes,
        },
    }


if __name__ == "__main__":
    import json
    data = get_pendientes_data()
    print(json.dumps(data, indent=2, ensure_ascii=False))
