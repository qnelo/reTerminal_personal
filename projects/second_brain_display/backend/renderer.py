"""
renderer.py
Genera vistas gráficas de 800x480 px de alta densidad y legibilidad para la pantalla
ePaper Spectra 6 del reTerminal E1002 utilizando Pillow y fuentes en negrita.
"""
from __future__ import annotations

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
SUBBAR_BOTTOM = 68
FOOTER_HEIGHT = 24
FOOTER_Y = 480 - FOOTER_HEIGHT


def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    path = FONT_PATH if bold else FONT_FALLBACK
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


FONT_HEADER = get_font(20, bold=True)
FONT_HEADER_INFO = get_font(14, bold=True)
FONT_SUBBAR = get_font(15, bold=True)
FONT_SUBBAR_RIGHT = get_font(13, bold=True)
FONT_ROW_NUM = get_font(13, bold=True)
FONT_ROW_CLIENT = get_font(12, bold=True)
FONT_ROW_TITLE = get_font(15, bold=True)
FONT_FOOTER = get_font(14, bold=True)


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
        if text_width(draw, text + "...", font) <= max_width:
            return text + "..."
    return text


def priority_color(color_name: str) -> tuple[int, int, int]:
    return {
        "RED": COLOR_RED,
        "YELLOW": COLOR_YELLOW,
        "GREEN": COLOR_GREEN,
    }.get(color_name, COLOR_BLACK)


def format_compact_due(vence_str: str) -> tuple[str, bool]:
    """Devuelve (texto_corto, es_critico) para mostrar fechas compactas en listas densas."""
    is_critical = "Hoy" in vence_str or "atraso" in vence_str
    text = vence_str if is_critical else vence_str.split(" (")[0]
    return text, is_critical


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


def draw_base_layout(
    view_title: str,
    page_indicator: str,
    timestamp_str: str,
    telemetry: dict[str, Any] | None = None,
) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (800, 480), COLOR_WHITE)
    draw = ImageDraw.Draw(img)

    vbat_val = _parse_float(telemetry, "vbat")
    temp_val = _parse_float(telemetry, "temp")
    hum_val = _parse_float(telemetry, "hum")

    # 1. Header superior compacto (38 px)
    draw.rectangle((0, 0, 800, HEADER_HEIGHT), fill=COLOR_BLUE)
    brand = "Pendientes Simpli"
    draw.text((14, 8), brand, fill=COLOR_WHITE, font=FONT_HEADER)
    brand_end_x = 14 + text_width(draw, brand, FONT_HEADER) + 16

    info_y = 11
    if vbat_val is not None:
        bat_pct = voltage_to_percentage(vbat_val)
        bat_color = COLOR_GREEN if bat_pct > 15 else COLOR_RED
        suffix = f"  [{page_indicator}]  •  {timestamp_str}  •  "
        pct_text = f"{bat_pct}%"
        fixed_right_w = text_width(draw, suffix, FONT_HEADER_INFO) + 26 + 5 + text_width(draw, pct_text, FONT_HEADER_INFO)
        max_title_w = 800 - 14 - fixed_right_w - brand_end_x
        safe_title = truncate_text(draw, view_title.upper(), max_title_w, FONT_HEADER_INFO)

        base_info = f"{safe_title}{suffix}"
        base_w = text_width(draw, base_info, FONT_HEADER_INFO)
        pct_w = text_width(draw, pct_text, FONT_HEADER_INFO)

        start_x = 800 - 14 - (base_w + 26 + 5 + pct_w)
        draw.text((start_x, info_y), base_info, fill=COLOR_WHITE, font=FONT_HEADER_INFO)

        bx = start_x + base_w
        by = 12
        draw.rounded_rectangle((bx, by, bx + 22, by + 13), radius=2, outline=COLOR_WHITE, width=2)
        draw.rectangle((bx + 23, by + 3, bx + 25, by + 10), fill=COLOR_WHITE)
        fill_w = max(2, int(18 * (bat_pct / 100.0)))
        draw.rectangle((bx + 2, by + 2, bx + 2 + fill_w, by + 11), fill=bat_color)
        draw.text((bx + 30, info_y), pct_text, fill=COLOR_WHITE, font=FONT_HEADER_INFO)
    else:
        suffix = f"  [{page_indicator}]  •  {timestamp_str}"
        max_title_w = 800 - 14 - text_width(draw, suffix, FONT_HEADER_INFO) - brand_end_x
        safe_title = truncate_text(draw, view_title.upper(), max_title_w, FONT_HEADER_INFO)
        right_info = f"{safe_title}{suffix}"
        rw = text_width(draw, right_info, FONT_HEADER_INFO)
        draw.text((800 - rw - 14, info_y), right_info, fill=COLOR_WHITE, font=FONT_HEADER_INFO)

    # 2. Footer inferior compacto (24 px)
    draw.rectangle((0, FOOTER_Y, 800, 480), fill=COLOR_BLACK)
    footer_left = "◄ Izq: Anterior  |  Der: Siguiente ►  |  Sync: Verde"
    draw.text((14, FOOTER_Y + 4), footer_left, fill=COLOR_WHITE, font=FONT_FOOTER)

    telem_parts = []
    if temp_val is not None:
        telem_parts.append(f"{temp_val:.1f}°C")
    if hum_val is not None:
        telem_parts.append(f"{hum_val:.0f}% RH")

    footer_right = "  •  ".join(telem_parts) if telem_parts else "Refresco: Lun-Vie 8:45 - 19:00"
    fr_w = text_width(draw, footer_right, FONT_FOOTER)
    draw.text((800 - fr_w - 14, FOOTER_Y + 4), footer_right, fill=COLOR_WHITE, font=FONT_FOOTER)

    return img, draw


def draw_kpi_subbar(draw: ImageDraw.ImageDraw, kpis: dict[str, int], right_text: str) -> None:
    y_sub = 42
    cx = 14
    for lbl, num, col in (
        ("Alta", kpis["alta"], COLOR_RED),
        ("Media", kpis["media"], COLOR_YELLOW),
        ("Baja", kpis["baja"], COLOR_GREEN),
    ):
        draw.rectangle((cx, y_sub + 4, cx + 14, y_sub + 18), fill=col, outline=COLOR_BLACK, width=1)
        txt = f"{num} {lbl}"
        draw.text((cx + 20, y_sub + 3), txt, fill=COLOR_BLACK, font=FONT_SUBBAR)
        cx += 20 + text_width(draw, txt, FONT_SUBBAR) + 22

    rw = text_width(draw, right_text, FONT_SUBBAR_RIGHT)
    draw.text((786 - rw, 47), right_text, fill=COLOR_BLACK, font=FONT_SUBBAR_RIGHT)
    draw.line((0, SUBBAR_BOTTOM, 800, SUBBAR_BOTTOM), fill=COLOR_BLACK, width=2)


def draw_task_row(
    draw: ImageDraw.ImageDraw,
    ry: int,
    row_h: int,
    index_num: int,
    item: dict[str, Any],
    show_client: bool,
    draw_divider: bool,
) -> None:
    p_color = priority_color(item["color"])
    draw.rounded_rectangle((12, ry + 6, 36, ry + row_h - 6), radius=3, fill=p_color)
    num_fg = COLOR_BLACK if p_color == COLOR_YELLOW else COLOR_WHITE
    num_str = str(index_num)
    nw = text_width(draw, num_str, FONT_ROW_NUM)
    draw.text((12 + (24 - nw) // 2, ry + 12), num_str, fill=num_fg, font=FONT_ROW_NUM)

    right_limit = 786
    if item.get("vence_str"):
        due_txt, is_critical = format_compact_due(item["vence_str"])
        dw = text_width(draw, due_txt, FONT_ROW_CLIENT)
        draw.text((786 - dw, ry + 13), due_txt, fill=COLOR_RED if is_critical else COLOR_BLACK, font=FONT_ROW_CLIENT)
        right_limit = 786 - dw - 10

    tx = 44
    if show_client:
        cli_txt = item["cliente"]
        draw.text((tx, ry + 13), cli_txt, fill=COLOR_BLUE, font=FONT_ROW_CLIENT)
        tx += text_width(draw, cli_txt, FONT_ROW_CLIENT) + 10
        draw.text((tx - 6, ry + 12), "·", fill=COLOR_BLACK, font=FONT_ROW_TITLE)
        tx += 4

    title = truncate_text(draw, item["titulo"], right_limit - tx, FONT_ROW_TITLE)
    draw.text((tx, ry + 11), title, fill=COLOR_BLACK, font=FONT_ROW_TITLE)

    if draw_divider:
        draw.line((12, ry + row_h, 788, ry + row_h), fill=COLOR_BLACK, width=1)


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
    tabs = data.get("tabs", [])
    if not tabs:
        img, draw = draw_base_layout("Resumen", "1/1", data.get("hora_corta", "--:--"), telemetry=telemetry)
        draw.text((24, 120), "No hay pendientes abiertos. ¡Todo al día!", fill=COLOR_GREEN, font=FONT_SUBBAR)
        return img

    resolved = tab_idx % len(tabs)
    tab = tabs[resolved]
    page_indicator = f"{resolved + 1}/{len(tabs)}"
    is_resumen = tab["tipo"] == "resumen"

    img, draw = draw_base_layout(tab["titulo"], page_indicator, data["hora_corta"], telemetry=telemetry)

    items = tab["items"][:9]
    if is_resumen:
        right_txt = f"TOTAL: {data['total_abiertos']}  •  ORDEN: PRIORIDAD"
    elif tab["total"] > len(items):
        right_txt = f"MOSTRANDO {len(items)} DE {tab['total']}"
    else:
        right_txt = f"CLIENTE: {tab['total']}  •  GLOBAL: {data['total_abiertos']}"

    draw_kpi_subbar(draw, tab["kpis"], right_txt)

    if not items:
        draw.text((24, 120), "No hay pendientes abiertos. ¡Todo al día!", fill=COLOR_GREEN, font=FONT_SUBBAR)
        return img

    y0 = 72
    row_h = 41
    for i, item in enumerate(items):
        ry = y0 + i * (row_h + 1)
        draw_task_row(draw, ry, row_h, i + 1, item, show_client=is_resumen, draw_divider=(i < len(items) - 1))

    return img


def render_view(view_ref: int | str, data: dict[str, Any], telemetry: dict[str, Any] | None = None) -> Image.Image:
    idx = resolve_tab_index(view_ref, data.get("tabs", []))
    return render_tab(idx, data, telemetry=telemetry)


if __name__ == "__main__":
    from data_provider import get_pendientes_data
    d = get_pendientes_data()
    out_dir = Path(__file__).resolve().parent / "previews"
    out_dir.mkdir(exist_ok=True)
    for i, tab in enumerate(d.get("tabs", [])):
        pic = render_tab(i, d)
        slug = tab["id"].replace(":", "_")
        pic_path = out_dir / f"{i:02d}_{slug}.png"
        pic.save(pic_path)
        print(f"Generado preview {i + 1}/{len(d['tabs'])}: {pic_path}")
