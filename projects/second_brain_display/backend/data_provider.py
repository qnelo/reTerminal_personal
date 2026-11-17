"""
data_provider.py
Consume datos del Second Brain (simpli-second-brain) usando herramientas del ecosistema
y los estructura en pestañas dinámicas (Resumen + 1 pestaña por cliente) para el reTerminal E1002.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from collections import defaultdict
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

PRIO_ORDER = {"muy-alta": 0, "alta": 1, "media-alta": 2, "media": 3, "baja": 4}


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
    """Devuelve código de color semántico para la pantalla Spectra 6."""
    if prioridad in ("muy-alta", "alta"):
        return "RED"
    elif prioridad in ("media-alta", "media"):
        return "YELLOW"
    elif prioridad == "baja":
        return "GREEN"
    return "BLACK"


def count_kpis(items: list[Any]) -> dict[str, int]:
    return {
        "alta": sum(1 for p in items if p.prioridad in ("muy-alta", "alta")),
        "media": sum(1 for p in items if p.prioridad in ("media-alta", "media")),
        "baja": sum(1 for p in items if p.prioridad == "baja"),
    }


def get_pendientes_data() -> dict[str, Any]:
    if sb is None:
        return {"error": "Módulo sb.py no encontrado en " + str(SB_TOOLS)}

    today = dt.date.today()
    pendientes, _ = sb.cargar()

    abiertos = [p for p in pendientes if p.estado == "abierto"]
    abiertos.sort(key=lambda p: (PRIO_ORDER.get(p.prioridad, 99), p.vence or dt.date(2099, 1, 1)))

    def to_card(p: Any, index: int = 1) -> dict[str, Any]:
        return {
            "index": index,
            "slug": p.slug,
            "titulo": p.titulo,
            "cliente": (p.cliente or "SIN-CLIENTE").upper(),
            "prioridad": p.prioridad,
            "color": get_priority_color(p.prioridad),
            "vence_str": format_due_date(p.vence, today),
            "es_urgente": p.prioridad in ("muy-alta", "alta") or bool(p.vence and (p.vence - today).days <= 1),
        }

    # Agrupar por cliente y ordenar por cantidad de pendientes (desc), luego mayor urgencia y nombre
    por_cliente: dict[str, list[Any]] = defaultdict(list)
    for p in abiertos:
        por_cliente[(p.cliente or "SIN-CLIENTE").upper()].append(p)

    clientes_ordenados = sorted(
        por_cliente.items(),
        key=lambda kv: (-len(kv[1]), min(PRIO_ORDER.get(p.prioridad, 99) for p in kv[1]), kv[0]),
    )

    tabs: list[dict[str, Any]] = [
        {
            "id": "resumen",
            "tipo": "resumen",
            "titulo": "Resumen",
            "total": len(abiertos),
            "kpis": count_kpis(abiertos),
            "items": [to_card(p, i + 1) for i, p in enumerate(abiertos[:9])],
            "top_clientes": [{"cliente": cli, "count": len(tasks)} for cli, tasks in clientes_ordenados],
        }
    ]

    for cli_name, tasks in clientes_ordenados:
        tabs.append(
            {
                "id": f"cliente:{cli_name.lower()}",
                "tipo": "cliente",
                "titulo": cli_name,
                "cliente": cli_name,
                "total": len(tasks),
                "kpis": count_kpis(tasks),
                "items": [to_card(p, i + 1) for i, p in enumerate(tasks[:9])],
            }
        )

    return {
        "timestamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hora_corta": dt.datetime.now().strftime("%H:%M"),
        "total_abiertos": len(abiertos),
        "total_clientes": len(clientes_ordenados),
        "total_vistas": len(tabs),
        "tabs": tabs,
    }


if __name__ == "__main__":
    import json
    data = get_pendientes_data()
    print(json.dumps(data, indent=2, ensure_ascii=False))
