"""
data_provider.py
Consume estadísticas del Second Brain (simpli-second-brain) reutilizando
tools/herdr-pendientes/estadistica.py y sb.py para el dashboard único del reTerminal E1002.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SB_TOOLS = Path(os.environ.get("SB_TOOLS") or "/home/pi/develop/personal/simpli-second-brain/tools/herdr-pendientes")
if str(SB_TOOLS) not in sys.path:
    sys.path.insert(0, str(SB_TOOLS))

try:
    import estadistica
    import sb
except ImportError:
    estadistica = None
    sb = None

MESES_ES = ("", "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")


def _empty_prio() -> dict[str, Any]:
    return {"n": 0, "prom": 0, "mediana": 0, "max": 0}


def build_stats_payload(
    vivos: list[Any],
    archivados: list[Any],
    clientes: set[str],
    today: dt.date,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    """Calcula el payload completo del dashboard estadístico a partir de listas de Pendiente."""
    now = now or dt.datetime.now()
    est = estadistica.calcular(vivos + archivados, clientes, today)

    gen = est["abiertos"].get(estadistica.GENERAL, {})
    kpis = {
        g: dict(gen[g]) if g in gen else _empty_prio()
        for g in estadistica.GRUPOS
    }
    total_abiertos = sum(kpis[g]["n"] for g in estadistica.GRUPOS)

    # Desglose por cliente o proyecto (tag resuelto por sb._cliente), usando el mismo filtro que estadistica.py
    por_tag: dict[str, dict[str, int]] = defaultdict(lambda: {"alta": 0, "media": 0, "baja": 0})
    for p in vivos:
        if p.cerrado or not p.abierto or p.prioridad not in estadistica.GRUPO:
            continue
        key = p.cliente or "sin-tag"
        por_tag[key][estadistica.GRUPO[p.prioridad]] += 1

    por_cliente = [
        {
            "nombre": k,
            "alta": v["alta"],
            "media": v["media"],
            "baja": v["baja"],
            "total": v["alta"] + v["media"] + v["baja"],
        }
        for k, v in por_tag.items()
    ]
    por_cliente.sort(key=lambda r: (-r["total"], -r["alta"], -r["media"], r["nombre"]))

    serie = est["serie"]
    delta_ayer = serie[-1]["total"] - serie[-2]["total"] if len(serie) >= 2 else 0
    delta_14d = serie[-1]["total"] - serie[0]["total"] if len(serie) >= 2 else 0
    fecha_corta = f"{today.day}-{MESES_ES[today.month]}"

    dashboard_tab = {
        "id": "estadistica",
        "tipo": "estadistica",
        "titulo": "Estadística",
        "hoy": est["hoy"],
        "fecha_corta": fecha_corta,
        "total": total_abiertos,
        "kpis": kpis,
        "delta_ayer": delta_ayer,
        "delta_14d": delta_14d,
        "por_cliente": por_cliente,
        "serie": serie,
    }

    return {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "hora_corta": now.strftime("%H:%M"),
        "fecha_corta": fecha_corta,
        "hoy": est["hoy"],
        "total_abiertos": total_abiertos,
        "total_clientes": len(por_cliente),
        "total_vistas": 1,
        "tabs": [dashboard_tab],
    }


def get_pendientes_data() -> dict[str, Any]:
    if sb is None or estadistica is None:
        return {"error": "Módulos sb.py / estadistica.py no encontrados en " + str(SB_TOOLS)}

    today = dt.date.today()
    vivos, _ = sb.cargar()
    return build_stats_payload(vivos, sb.archivados(), sb.clientes(), today)


if __name__ == "__main__":
    import json
    data = get_pendientes_data()
    print(json.dumps(data, indent=2, ensure_ascii=False))
