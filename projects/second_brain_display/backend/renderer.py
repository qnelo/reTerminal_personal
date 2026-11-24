"""
renderer.py
Genera el dashboard estadístico de 800x480 px para la pantalla ePaper Spectra 6
del reTerminal E1002 utilizando Pillow, paleta pura de 6 tintas y fuentes en negrita.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any
from PIL import Image, ImageDraw, ImageFont

# Paleta calibrada para el umbral duro de colorconv.h (Spectra 6):
# todos los colores caen en la tinta esperada en el panel físico.
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_RED = (210, 28, 28)
COLOR_BLUE = (28, 68, 175)
COLOR_YELLOW = (235, 200, 20)
COLOR_GREEN = (20, 140, 48)

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

HEADER_HEIGHT = 38
MAX_CLIENT_ROWS = 7


def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    path = FONT_PATH if bold else FONT_FALLBACK
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


FONT_HEADER = get_font(20)
FONT_HEADER_INFO = get_font(14)
FONT_KPI_TITLE = get_font(13)
FONT_KPI_PRIO = get_font(14)
FONT_KPI_TOTAL_BIG = get_font(42)
FONT_KPI_TOTAL_MED = get_font(34)
FONT_KPI_NUM = get_font(38)
FONT_KPI_NUM_SM = get_font(30)
FONT_KPI_SUB = get_font(13)
FONT_KPI_DELTA_SM = get_font(12)
FONT_PANEL_TITLE = get_font(14)
FONT_PANEL_META = get_font(12)
FONT_CLIENT_NAME = get_font(13)
FONT_CLIENT_TOT = get_font(16)
FONT_AXIS = get_font(11)
FONT_BAR_TOP = get_font(12)


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def truncate_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, font: ImageFont.FreeTypeFont) -> str:
    if max_width <= 0:
        return ""
    if text_width(draw, text, font) <= max_width:
        return text
    while len(text) > 3:
        text = text[:-1]
        if text_width(draw, text + "…", font) <= max_width:
            return text + "…"
    return text


def voltage_to_percentage(v: float) -> int:
    """
    Curva de calibración oficial de Seeed Studio para el reTerminal E1002.
    Compensa la caída del MOSFET de activación (GPIO21) y las tolerancias del divisor
    resistivo (GPIO1), donde el circuito de carga corta entre 4.10V y 4.15V.
    """
    if v >= 4.12:
        return 100
    if v <= 3.27:
        return 0
    points = [
        (4.12, 100),
        (3.96, 90),
        (3.91, 80),
        (3.85, 70),
        (3.80, 60),
        (3.75, 50),
        (3.68, 40),
        (3.58, 30),
        (3.49, 20),
        (3.41, 10),
        (3.30, 5),
        (3.27, 0),
    ]
    for i in range(len(points) - 1):
        v_high, p_high = points[i]
        v_low, p_low = points[i + 1]
        if v >= v_low:
            pct = p_low + (v - v_low) / (v_high - v_low) * (p_high - p_low)
            return min(100, max(0, int(round(pct))))
    return 0


def _parse_float(telemetry: dict[str, Any] | None, key: str) -> float | None:
    if not telemetry or telemetry.get(key) is None:
        return None
    try:
        return float(telemetry[key])
    except (ValueError, TypeError):
        return None


def _fmt_delta(val: int) -> str:
    if val > 0:
        return f"+{val}"
    return str(val)


def _draw_dashed_hline(draw: ImageDraw.ImageDraw, x0: int, x1: int, y: int, dash: int = 3, gap: int = 5) -> None:
    x = x0
    while x < x1:
        draw.line((x, y, min(x + dash, x1), y), fill=COLOR_BLACK, width=1)
        x += dash + gap


def _distribute_lengths(values: list[int], total_px: int, min_seg_px: int) -> list[int]:
    """Reparte total_px proporcionalmente entre values asegurando suma exacta y mínimo visible por segmento > 0."""
    n = len(values)
    nonzero = [i for i, v in enumerate(values) if v > 0]
    if not nonzero or total_px <= 0:
        return [0] * n

    eff_min = min(min_seg_px, max(1, total_px // len(nonzero)))
    total_val = sum(values[i] for i in nonzero)
    segs = [0] * n
    for i in nonzero:
        segs[i] = max(eff_min, int(round((values[i] / total_val) * total_px)))

    # Ajustar diferencia de redondeo sobre el segmento más grande (manteniendo >= eff_min)
    diff = sum(segs) - total_px
    while diff != 0:
        step = -1 if diff > 0 else 1
        candidates = [i for i in nonzero if segs[i] + step >= eff_min]
        if not candidates:
            break
        target = max(candidates, key=lambda i: (segs[i], values[i])) if diff > 0 else max(candidates, key=lambda i: values[i])
        segs[target] += step
        diff += step
    return segs


def _calc_y_scale(max_val: int) -> tuple[int, int]:
    """Devuelve (y_max, step) limpios con holgura superior para etiquetas encima de las barras."""
    if max_val <= 0:
        return 5, 1
    if max_val <= 4:
        return 5, 1
    if max_val <= 24:
        y_max = ((max_val + 6) // 5) * 5
        return y_max, 5
    if max_val <= 50:
        y_max = ((max_val + 11) // 10) * 10
        return y_max, 10
    step = 20 if max_val <= 100 else 50
    y_max = ((max_val + step + 2) // step) * step
    return y_max, step


def draw_header(
    draw: ImageDraw.ImageDraw,
    fecha_corta: str,
    timestamp_str: str,
    telemetry: dict[str, Any] | None = None,
) -> None:
    """Header único (38 px): Marca + fecha a la izq; Temp • Hum • Hora • Batería a la der."""
    draw.rectangle((0, 0, 800, HEADER_HEIGHT), fill=COLOR_BLUE)

    brand = "Pendientes Simpli"
    draw.text((14, 7), brand, fill=COLOR_WHITE, font=FONT_HEADER)
    if fecha_corta:
        brand_end = 14 + text_width(draw, brand, FONT_HEADER)
        draw.text((brand_end + 10, 12), f"•  {fecha_corta}", fill=COLOR_YELLOW, font=FONT_HEADER_INFO)

    vbat_val = _parse_float(telemetry, "vbat")
    temp_val = _parse_float(telemetry, "temp")
    hum_val = _parse_float(telemetry, "hum")

    parts: list[str] = []
    if temp_val is not None:
        parts.append(f"{temp_val:.1f}°C")
    if hum_val is not None:
        parts.append(f"{hum_val:.0f}% RH")
    if timestamp_str:
        parts.append(timestamp_str)

    info_y = 11
    if vbat_val is not None:
        bat_pct = voltage_to_percentage(vbat_val)
        bat_color = COLOR_GREEN if bat_pct > 15 else COLOR_RED
        base = "  •  ".join(parts) + ("  •  " if parts else "")
        pct_text = f"{bat_pct}%"
        base_w = text_width(draw, base, FONT_HEADER_INFO)
        pct_w = text_width(draw, pct_text, FONT_HEADER_INFO)
        start_x = 800 - 14 - (base_w + 26 + 5 + pct_w)
        if base:
            draw.text((start_x, info_y), base, fill=COLOR_WHITE, font=FONT_HEADER_INFO)

        bx = start_x + base_w
        by = 12
        draw.rounded_rectangle((bx, by, bx + 22, by + 13), radius=2, outline=COLOR_WHITE, width=2)
        draw.rectangle((bx + 23, by + 3, bx + 25, by + 10), fill=COLOR_WHITE)
        fill_w = max(2, int(18 * (bat_pct / 100.0)))
        draw.rectangle((bx + 2, by + 2, bx + 2 + fill_w, by + 11), fill=bat_color)
        draw.text((bx + 30, info_y), pct_text, fill=COLOR_WHITE, font=FONT_HEADER_INFO)
    elif parts:
        right_info = "  •  ".join(parts)
        rw = text_width(draw, right_info, FONT_HEADER_INFO)
        draw.text((800 - rw - 14, info_y), right_info, fill=COLOR_WHITE, font=FONT_HEADER_INFO)


def _draw_kpi_strip(draw: ImageDraw.ImageDraw, tab: dict[str, Any]) -> None:
    total = int(tab.get("total", 0))
    kpis = tab.get("kpis", {})
    delta_ayer = int(tab.get("delta_ayer", 0))
    delta_14d = int(tab.get("delta_14d", 0))

    y0, y1 = 48, 134

    # 1. Tarjeta TOTAL ABIERTOS (azul sólido)
    cx, w_tot = 12, 224
    draw.rounded_rectangle((cx, y0, cx + w_tot, y1), radius=6, fill=COLOR_BLUE, outline=COLOR_BLACK, width=2)
    draw.text((cx + 12, y0 + 8), "TOTAL ABIERTOS", fill=COLOR_WHITE, font=FONT_KPI_TITLE)
    tot_str = str(total)
    tot_font = FONT_KPI_TOTAL_BIG if total < 100 else FONT_KPI_TOTAL_MED
    tot_y = y0 + 25 if total < 100 else y0 + 30
    draw.text((cx + 14, tot_y), tot_str, fill=COLOR_WHITE, font=tot_font)

    dx = cx + 14 + max(60, text_width(draw, tot_str, tot_font) + 12)
    draw.text((dx, y0 + 36), f"{_fmt_delta(delta_ayer)} vs ayer", fill=COLOR_WHITE, font=FONT_KPI_SUB)
    draw.text((dx, y0 + 56), f"{_fmt_delta(delta_14d)} en 14 días", fill=COLOR_YELLOW, font=FONT_KPI_DELTA_SM)

    # 2. Tarjetas ALTA / MEDIA / BAJA
    cx += w_tot + 10
    w_card = 174
    specs = (
        ("alta", "ALTA", COLOR_RED, COLOR_WHITE),
        ("media", "MEDIA", COLOR_YELLOW, COLOR_BLACK),
        ("baja", "BAJA", COLOR_GREEN, COLOR_WHITE),
    )
    for key, label, accent, fg_hdr in specs:
        info = kpis.get(key) or {}
        num = int(info.get("n", 0))
        prom = info.get("prom", 0)
        sub = f"prom {prom:g}d" if num > 0 else "sin abiertos"

        # Esquinas redondeadas limpias: banda superior de color + cuerpo blanco + borde negro encima
        draw.rounded_rectangle((cx, y0, cx + w_card, y1), radius=6, fill=accent)
        draw.rounded_rectangle((cx, y0 + 20, cx + w_card, y1), radius=6, fill=COLOR_WHITE)
        draw.rectangle((cx + 2, y0 + 18, cx + w_card - 2, y0 + 26), fill=accent)
        draw.line((cx, y0 + 26, cx + w_card, y0 + 26), fill=COLOR_BLACK, width=1)
        draw.rounded_rectangle((cx, y0, cx + w_card, y1), radius=6, outline=COLOR_BLACK, width=2)

        draw.text((cx + 10, y0 + 6), label, fill=fg_hdr, font=FONT_KPI_PRIO)
        num_str = str(num)
        num_font = FONT_KPI_NUM if num < 100 else FONT_KPI_NUM_SM
        num_y = y0 + 33 if num < 100 else y0 + 39
        draw.text((cx + 12, num_y), num_str, fill=COLOR_BLACK, font=num_font)
        nw = text_width(draw, num_str, num_font)
        sub_txt = truncate_text(draw, sub, (cx + w_card - 8) - (cx + 12 + nw + 8), FONT_KPI_SUB)
        draw.text((cx + 12 + nw + 8, y0 + 50), sub_txt, fill=COLOR_BLACK, font=FONT_KPI_SUB)
        cx += w_card + 10


def _collapse_clients(grupos: list[dict[str, Any]], max_rows: int = MAX_CLIENT_ROWS) -> list[dict[str, Any]]:
    if len(grupos) <= max_rows:
        return grupos
    top = list(grupos[: max_rows - 1])
    rest = grupos[max_rows - 1 :]
    top.append(
        {
            "nombre": f"OTROS (+{len(rest)})",
            "alta": sum(r.get("alta", 0) for r in rest),
            "media": sum(r.get("media", 0) for r in rest),
            "baja": sum(r.get("baja", 0) for r in rest),
            "total": sum(r.get("total", 0) for r in rest),
        }
    )
    return top


def _draw_clients_panel(draw: ImageDraw.ImageDraw, tab: dict[str, Any]) -> None:
    px0, py0, px1, py1 = 12, 146, 314, 468
    draw.rounded_rectangle((px0, py0, px1, py1), radius=6, outline=COLOR_BLACK, width=2, fill=COLOR_WHITE)
    draw.text((px0 + 12, py0 + 8), "POR CLIENTE / PROYECTO", fill=COLOR_BLACK, font=FONT_PANEL_TITLE)

    raw_grupos = tab.get("por_cliente") or []
    cnt_txt = f"{len(raw_grupos)} activos" if len(raw_grupos) != 1 else "1 activo"
    draw.text((px1 - 12 - text_width(draw, cnt_txt, FONT_PANEL_META), py0 + 10), cnt_txt, fill=COLOR_BLUE, font=FONT_PANEL_META)
    draw.line((px0, py0 + 30, px1, py0 + 30), fill=COLOR_BLACK, width=1)

    if not raw_grupos:
        msg = "¡Todo al día!"
        mw = text_width(draw, msg, FONT_CLIENT_TOT)
        draw.text((px0 + (px1 - px0 - mw) // 2, py0 + 140), msg, fill=COLOR_GREEN, font=FONT_CLIENT_TOT)
        return

    grupos = _collapse_clients(raw_grupos, MAX_CLIENT_ROWS)
    max_cli = max((g["total"] for g in grupos), default=1)
    ry = py0 + 38
    avail_h = py1 - ry - 6
    row_h = min(42, max(28, avail_h // len(grupos)))
    bar_max_w = 132

    for idx, g in enumerate(grupos):
        name = truncate_text(draw, str(g["nombre"]).upper(), 112, FONT_CLIENT_NAME)
        draw.text((px0 + 10, ry + (row_h - 15) // 2), name, fill=COLOR_BLACK, font=FONT_CLIENT_NAME)

        tot_w = max(8, int(round((g["total"] / max_cli) * bar_max_w)))
        seg_ws = _distribute_lengths([g.get("alta", 0), g.get("media", 0), g.get("baja", 0)], tot_w, min_seg_px=6)

        cur_x = px0 + 126
        by0 = ry + (row_h - 18) // 2
        by1 = by0 + 18
        for sw, col in zip(seg_ws, (COLOR_RED, COLOR_YELLOW, COLOR_GREEN)):
            if sw <= 0:
                continue
            draw.rectangle((cur_x, by0, cur_x + sw, by1), fill=col, outline=COLOR_BLACK, width=1)
            cur_x += sw

        t_str = str(g["total"])
        draw.text((px1 - 12 - text_width(draw, t_str, FONT_CLIENT_TOT), ry + (row_h - 18) // 2), t_str, fill=COLOR_BLACK, font=FONT_CLIENT_TOT)
        if idx < len(grupos) - 1:
            draw.line((px0 + 10, ry + row_h - 1, px1 - 10, ry + row_h - 1), fill=COLOR_BLACK, width=1)
        ry += row_h


def _draw_series_chart(draw: ImageDraw.ImageDraw, tab: dict[str, Any]) -> None:
    x0, y0, x1, y1 = 324, 146, 788, 468
    draw.rounded_rectangle((x0, y0, x1, y1), radius=6, outline=COLOR_BLACK, width=2, fill=COLOR_WHITE)
    draw.text((x0 + 12, y0 + 8), "ÚLTIMAS 2 SEMANAS (14 DÍAS)", fill=COLOR_BLACK, font=FONT_PANEL_TITLE)

    # Leyenda arriba a la derecha
    leg_items = (("Alta", COLOR_RED), ("Media", COLOR_YELLOW), ("Baja", COLOR_GREEN))
    lx = x1 - 12
    for lbl, col in reversed(leg_items):
        lw = text_width(draw, lbl, FONT_PANEL_META)
        lx -= lw
        draw.text((lx, y0 + 10), lbl, fill=COLOR_BLACK, font=FONT_PANEL_META)
        lx -= 16
        draw.rectangle((lx, y0 + 11, lx + 11, y0 + 22), fill=col, outline=COLOR_BLACK, width=1)
        lx -= 12

    draw.line((x0, y0 + 30, x1, y0 + 30), fill=COLOR_BLACK, width=1)

    serie = tab.get("serie") or []
    if not serie:
        msg = "Sin datos históricos"
        mw = text_width(draw, msg, FONT_PANEL_TITLE)
        draw.text((x0 + (x1 - x0 - mw) // 2, y0 + 150), msg, fill=COLOR_BLACK, font=FONT_PANEL_TITLE)
        return

    gx0 = x0 + 34
    gx1 = x1 - 12
    gy0 = y0 + 50
    gy1 = y1 - 28
    plot_h = gy1 - gy0

    max_val = max((f.get("total", 0) for f in serie), default=0)
    y_max, step = _calc_y_scale(max_val)

    for val in range(0, y_max + 1, step):
        py = gy1 - int(round((val / y_max) * plot_h))
        if val > 0:
            _draw_dashed_hline(draw, gx0, gx1, py)
        lbl = str(val)
        draw.text((gx0 - 6 - text_width(draw, lbl, FONT_AXIS), py - 6), lbl, fill=COLOR_BLACK, font=FONT_AXIS)

    draw.line((gx0, gy0 - 4, gx0, gy1), fill=COLOR_BLACK, width=2)
    draw.line((gx0, gy1, gx1, gy1), fill=COLOR_BLACK, width=2)

    n = len(serie)
    slot_w = (gx1 - gx0 - 6) / max(n, 1)
    bar_w = max(12, int(slot_w * 0.68))

    for i, f in enumerate(serie):
        cx = int(gx0 + 3 + (i + 0.5) * slot_w)
        bx0 = cx - bar_w // 2
        bx1 = bx0 + bar_w
        is_today = (i == n - 1)

        total = int(f.get("total", 0))
        tot_h = int(round((total / y_max) * plot_h)) if total > 0 else 0
        seg_hs = _distribute_lengths(
            [int(f.get("alta", 0)), int(f.get("media", 0)), int(f.get("baja", 0))],
            tot_h,
            min_seg_px=3,
        )

        # Apilado: Alta abajo (rojo), Media medio (amarillo), Baja arriba (verde)
        cur_y = gy1
        for sh, col in zip(seg_hs, (COLOR_RED, COLOR_YELLOW, COLOR_GREEN)):
            if sh <= 0:
                continue
            top_y = cur_y - sh
            draw.rectangle((bx0, top_y, bx1, cur_y), fill=col, outline=COLOR_BLACK, width=1)
            cur_y = top_y

        # Total encima de la barra con máscara blanca para no chocar con líneas punteadas
        tot_s = str(total)
        tot_w = text_width(draw, tot_s, FONT_BAR_TOP)
        tx = cx - tot_w // 2
        ty = cur_y - 16
        draw.rectangle((tx - 2, ty - 1, tx + tot_w + 2, ty + 13), fill=COLOR_WHITE)
        draw.text((tx, ty), tot_s, fill=COLOR_BLUE if is_today else COLOR_BLACK, font=FONT_BAR_TOP)

        # Día en el eje X
        try:
            d = dt.date.fromisoformat(str(f["dia"]))
            xlbl = f"{d.day:02d}"
        except (ValueError, KeyError):
            xlbl = str(i + 1)

        xw = text_width(draw, xlbl, FONT_AXIS)
        if is_today:
            pad_w = xw + 8
            draw.rounded_rectangle((cx - pad_w // 2, gy1 + 4, cx + pad_w // 2, gy1 + 21), radius=3, fill=COLOR_BLUE)
            draw.text((cx - xw // 2, gy1 + 6), xlbl, fill=COLOR_WHITE, font=FONT_AXIS)
        else:
            draw.text((cx - xw // 2, gy1 + 6), xlbl, fill=COLOR_BLACK, font=FONT_AXIS)


def resolve_tab_index(view_ref: int | str, tabs: list[dict[str, Any]]) -> int:
    if not tabs:
        return 0
    if isinstance(view_ref, int):
        return view_ref % len(tabs)
    if view_ref.lstrip("-").isdigit():
        return int(view_ref) % len(tabs)
    for i, tab in enumerate(tabs):
        if tab.get("id") == view_ref or tab.get("titulo", "").lower() == view_ref.lower():
            return i
    return 0


def render_tab(tab_idx: int, data: dict[str, Any], telemetry: dict[str, Any] | None = None) -> Image.Image:
    img = Image.new("RGB", (800, 480), COLOR_WHITE)
    draw = ImageDraw.Draw(img)

    tabs = data.get("tabs") or []
    hora_corta = data.get("hora_corta", "--:--")
    if not tabs:
        draw_header(draw, data.get("fecha_corta", ""), hora_corta, telemetry=telemetry)
        msg = data.get("error") or "Sin datos de estadísticas disponibles."
        draw.text((24, 120), msg, fill=COLOR_RED, font=FONT_PANEL_TITLE)
        return img

    tab = tabs[tab_idx % len(tabs)]
    fecha_corta = tab.get("fecha_corta") or data.get("fecha_corta", "")
    draw_header(draw, fecha_corta, hora_corta, telemetry=telemetry)
    _draw_kpi_strip(draw, tab)
    _draw_clients_panel(draw, tab)
    _draw_series_chart(draw, tab)
    return img


def render_view(view_ref: int | str, data: dict[str, Any], telemetry: dict[str, Any] | None = None) -> Image.Image:
    idx = resolve_tab_index(view_ref, data.get("tabs", []))
    return render_tab(idx, data, telemetry=telemetry)


if __name__ == "__main__":
    from data_provider import get_pendientes_data
    d = get_pendientes_data()
    out_dir = Path(__file__).resolve().parent / "previews"
    out_dir.mkdir(exist_ok=True)
    pic = render_view(0, d)
    pic_path = out_dir / "00_estadistica.png"
    pic.save(pic_path, format="PNG", optimize=True)
    print(f"Generado preview: {pic_path} ({pic_path.stat().st_size} bytes)")
