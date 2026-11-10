"""
renderer.py
Genera vistas gráficas de 800x480 px de ultra-alta legibilidad para la pantalla
ePaper Spectra 6 del reTerminal E1002 utilizando Pillow y fuentes en negrita.
"""
from __future__ import annotations

import io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import Any

# Paleta oficial optimizada para Spectra 6
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_RED = (220, 38, 38)
COLOR_BLUE = (30, 58, 138)
COLOR_YELLOW = (217, 119, 6)
COLOR_GREEN = (22, 101, 52)
COLOR_LIGHT_GRAY = (243, 244, 246)
COLOR_CARD_BORDER = (156, 163, 175)

# Carga de fuentes del sistema
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    path = FONT_PATH if bold else FONT_FALLBACK
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

FONT_HEADER = get_font(22, bold=True)
FONT_KPI_NUM = get_font(36, bold=True)
FONT_KPI_LABEL = get_font(16, bold=True)
FONT_CARD_TITLE = get_font(19, bold=True)
FONT_BADGE = get_font(15, bold=True)
FONT_FOOTER = get_font(15, bold=True)
FONT_SECTION = get_font(20, bold=True)


def draw_rounded_rectangle(draw: ImageDraw.ImageDraw, xy: tuple, fill=None, outline=None, width=1, radius=6):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_badge(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, bg_color: tuple, text_color: tuple = COLOR_WHITE) -> int:
    """Dibuja una pastilla de color y devuelve la posición X final para concatenar."""
    bbox = draw.textbbox((0, 0), text, font=FONT_BADGE)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 8, 4
    draw_rounded_rectangle(draw, (x, y, x + tw + pad_x * 2, y + th + pad_y * 2), fill=bg_color, radius=4)
    draw.text((x + pad_x, y + pad_y - 1), text, fill=text_color, font=FONT_BADGE)
    return x + tw + pad_x * 2 + 8


def truncate_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, font: ImageFont.FreeTypeFont) -> str:
    if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
        return text
    while len(text) > 3:
        text = text[:-1]
        if draw.textbbox((0, 0), text + "...", font=font)[2] <= max_width:
            return text + "..."
    return text


def voltage_to_percentage(v: float) -> int:
    """Calcula el porcentaje de carga aproximado de una batería Li-ion (3.4V a 4.2V)."""
    if v >= 4.20:
        return 100
    if v <= 3.40:
        return 0
    points = [
        (4.20, 100),
        (4.05, 90),
        (3.95, 75),
        (3.85, 60),
        (3.75, 40),
        (3.65, 20),
        (3.50, 10),
        (3.40, 0),
    ]
    for i in range(len(points) - 1):
        v_high, p_high = points[i]
        v_low, p_low = points[i + 1]
        if v >= v_low:
            pct = p_low + (v - v_low) / (v_high - v_low) * (p_high - p_low)
            return int(round(pct))
    return 0


def draw_base_layout(view_title: str, page_indicator: str, timestamp_str: str, telemetry: dict[str, Any] | None = None) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (800, 480), COLOR_WHITE)
    draw = ImageDraw.Draw(img)

    vbat_val = None
    if telemetry and telemetry.get("vbat") is not None:
        try:
            vbat_val = float(telemetry["vbat"])
        except (ValueError, TypeError):
            pass

    temp_val = None
    if telemetry and telemetry.get("temp") is not None:
        try:
            temp_val = float(telemetry["temp"])
        except (ValueError, TypeError):
            pass

    hum_val = None
    if telemetry and telemetry.get("hum") is not None:
        try:
            hum_val = float(telemetry["hum"])
        except (ValueError, TypeError):
            pass

    # 1. Header superior (46 px)
    draw.rectangle((0, 0, 800, 46), fill=COLOR_BLUE)
    draw.text((16, 12), "Pendientes Simpli", fill=COLOR_WHITE, font=FONT_HEADER)
    
    # Bloque derecho de la cabecera (Vista, Página, Hora y Batería)
    if vbat_val is not None:
        bat_pct = voltage_to_percentage(vbat_val)
        # Verde desde 15% hacia arriba, roja desde 15% hacia abajo
        bat_color = (34, 197, 94) if bat_pct > 15 else (220, 38, 38)

        base_info = f"{view_title.upper()}  [{page_indicator}]  •  {timestamp_str}  •  "
        bbox_base = draw.textbbox((0, 0), base_info, font=FONT_BADGE)
        base_w = bbox_base[2] - bbox_base[0]

        pct_text = f"{bat_pct}%"
        bbox_p = draw.textbbox((0, 0), pct_text, font=FONT_BADGE)
        pct_w = bbox_p[2] - bbox_p[0]

        # Ancho total: texto base + icono (26px) + gap (5px) + pct_text
        total_w = base_w + 26 + 5 + pct_w
        start_x = 800 - 16 - total_w

        # Dibujar texto base en blanco
        draw.text((start_x, 15), base_info, fill=COLOR_WHITE, font=FONT_BADGE)

        # Dibujar icono de batería
        bx = start_x + base_w
        by = 16
        # Contorno y borne positivo
        draw.rounded_rectangle((bx, by, bx + 22, by + 13), radius=2, outline=bat_color, width=2)
        draw.rounded_rectangle((bx + 23, by + 3, bx + 25, by + 10), radius=1, fill=bat_color)
        # Relleno interior proporcional a la carga
        fill_w = max(1, int(17 * (bat_pct / 100.0)))
        draw.rounded_rectangle((bx + 2, by + 2, bx + 2 + fill_w, by + 11), radius=1, fill=bat_color)

        # Texto de porcentaje siempre en blanco
        draw.text((bx + 30, 15), pct_text, fill=COLOR_WHITE, font=FONT_BADGE)
    else:
        right_info = f"{view_title.upper()}  [{page_indicator}]  •  {timestamp_str}"
        bbox_r = draw.textbbox((0, 0), right_info, font=FONT_BADGE)
        draw.text((800 - (bbox_r[2] - bbox_r[0]) - 16, 15), right_info, fill=COLOR_WHITE, font=FONT_BADGE)

    # 2. Footer inferior (28 px)
    draw.rectangle((0, 452, 800, 480), fill=COLOR_BLACK)
    footer_left = "◄ Izq: Anterior   |   Der: Siguiente ►   |   Sync: Verde"
    draw.text((16, 457), footer_left, fill=COLOR_WHITE, font=FONT_FOOTER)

    # Detalle de telemetría a la derecha del footer (solo temperatura y humedad)
    telem_parts = []
    if temp_val is not None:
        telem_parts.append(f"{temp_val:.1f}°C")
    if hum_val is not None:
        telem_parts.append(f"{hum_val:.0f}% RH")

    if telem_parts:
        footer_right = "  •  ".join(telem_parts)
    else:
        footer_right = "Refresco: Lun-Vie 8:45 - 19:00"

    bbox_fr = draw.textbbox((0, 0), footer_right, font=FONT_FOOTER)
    draw.text((800 - (bbox_fr[2] - bbox_fr[0]) - 16, 457), footer_right, fill=COLOR_WHITE, font=FONT_FOOTER)

    return img, draw


def render_view_resumen(data: dict[str, Any], telemetry: dict[str, Any] | None = None) -> Image.Image:
    v = data["vistas"]["resumen"]
    img, draw = draw_base_layout("Resumen", "1/5", data["hora_corta"], telemetry=telemetry)

    # 3 Cajas KPI de Resumen
    kpis = [
        ("ALTA PRIORIDAD", str(v["kpis"]["alta"]), COLOR_RED),
        ("MEDIA PRIORIDAD", str(v["kpis"]["media"]), COLOR_YELLOW),
        ("BAJA PRIORIDAD", str(v["kpis"]["baja"]), COLOR_GREEN),
    ]

    card_w = 248
    for i, (label, count, color) in enumerate(kpis):
        x = 16 + i * (card_w + 14)
        draw_rounded_rectangle(draw, (x, 56, x + card_w, 126), fill=COLOR_LIGHT_GRAY, outline=color, width=2, radius=6)
        # Pastilla de color lateral
        draw_rounded_rectangle(draw, (x, 56, x + 8, 126), fill=color, radius=2)
        draw.text((x + 22, 64), count, fill=color, font=FONT_KPI_NUM)
        draw.text((x + 22, 102), label, fill=COLOR_BLACK, font=FONT_KPI_LABEL)

    # Subtítulo
    draw.text((16, 140), "TAREAS DE MÁXIMA PRIORIDAD Y URGENCIA", fill=COLOR_BLACK, font=FONT_SECTION)
    draw.line((16, 166, 784, 166), fill=COLOR_CARD_BORDER, width=1)

    # Lista de 4 tarjetas urgentes
    y_start = 176
    card_h = 62
    for i, item in enumerate(v["top_urgentes"][:4]):
        cy = y_start + i * (card_h + 6)
        draw_rounded_rectangle(draw, (16, cy, 784, cy + card_h), fill=COLOR_LIGHT_GRAY, outline=COLOR_CARD_BORDER, width=1, radius=6)
        
        # Borde izquierdo de color según prioridad
        badge_color = COLOR_RED if item["color"] == "RED" else COLOR_YELLOW
        draw_rounded_rectangle(draw, (16, cy, 22, cy + card_h), fill=badge_color, radius=2)

        # Badges (Cliente y Vencimiento)
        bx = 32
        bx = draw_badge(draw, bx, cy + 10, item["cliente"], COLOR_BLUE)
        if item["vence_str"]:
            draw_badge(draw, bx, cy + 10, item["vence_str"], COLOR_RED if "Hoy" in item["vence_str"] else COLOR_BLACK)

        # Título de la tarea
        title = truncate_text(draw, item["titulo"], 730, FONT_CARD_TITLE)
        draw.text((32, cy + 34), title, fill=COLOR_BLACK, font=FONT_CARD_TITLE)

    return img


def render_view_list(data: dict[str, Any], view_key: str, view_num: str, telemetry: dict[str, Any] | None = None) -> Image.Image:
    v = data["vistas"][view_key]
    img, draw = draw_base_layout(v["titulo"], view_num, data["hora_corta"], telemetry=telemetry)

    total = v["total"]
    draw.text((16, 56), f"{v['titulo'].upper()}  ({total} PENDIENTES)", fill=COLOR_BLACK, font=FONT_SECTION)
    draw.line((16, 82, 784, 82), fill=COLOR_CARD_BORDER, width=1)

    items = v["items"]
    if not items:
        draw.text((32, 140), "No hay pendientes en esta categoría. ¡Todo al día!", fill=COLOR_GREEN, font=FONT_CARD_TITLE)
        return img

    y_start = 92
    card_h = 64
    badge_bg = COLOR_RED if v["color"] == "RED" else (COLOR_YELLOW if v["color"] == "YELLOW" else COLOR_GREEN)

    for i, item in enumerate(items[:5]):
        cy = y_start + i * (card_h + 6)
        draw_rounded_rectangle(draw, (16, cy, 784, cy + card_h), fill=COLOR_LIGHT_GRAY, outline=COLOR_CARD_BORDER, width=1, radius=6)
        draw_rounded_rectangle(draw, (16, cy, 22, cy + card_h), fill=badge_bg, radius=2)

        bx = 32
        bx = draw_badge(draw, bx, cy + 10, item["cliente"], COLOR_BLUE)
        if item["vence_str"]:
            draw_badge(draw, bx, cy + 10, item["vence_str"], COLOR_RED if "Hoy" in item["vence_str"] else COLOR_BLACK)

        title = truncate_text(draw, item["titulo"], 730, FONT_CARD_TITLE)
        draw.text((32, cy + 36), title, fill=COLOR_BLACK, font=FONT_CARD_TITLE)

    return img


def render_view_clientes(data: dict[str, Any], telemetry: dict[str, Any] | None = None) -> Image.Image:
    v = data["vistas"]["clientes"]
    img, draw = draw_base_layout("Por Cliente", "5/5", data["hora_corta"], telemetry=telemetry)

    draw.text((16, 56), f"PENDIENTES AGRUPADOS POR CUENTA Y CLIENTE ({v['total_clientes']} CLIENTES)", fill=COLOR_BLACK, font=FONT_SECTION)
    draw.line((16, 82, 784, 82), fill=COLOR_CARD_BORDER, width=1)

    y_pos = 92
    for grupo in v["grupos"][:3]:
        # Encabezado del cliente
        client_header = f"• {grupo['cliente']} ({grupo['conteo']} pendientes)"
        draw.text((20, y_pos), client_header, fill=COLOR_BLUE, font=FONT_SECTION)
        y_pos += 28

        for item in grupo["tareas"][:2]:
            draw_rounded_rectangle(draw, (24, y_pos, 784, y_pos + 38), fill=COLOR_LIGHT_GRAY, outline=COLOR_CARD_BORDER, width=1, radius=4)
            p_color = COLOR_RED if item["color"] == "RED" else (COLOR_YELLOW if item["color"] == "YELLOW" else COLOR_GREEN)
            draw_rounded_rectangle(draw, (24, y_pos, 28, y_pos + 38), fill=p_color, radius=2)

            t_text = truncate_text(draw, item["titulo"], 620, FONT_BADGE)
            draw.text((36, y_pos + 10), t_text, fill=COLOR_BLACK, font=FONT_BADGE)

            if item["vence_str"]:
                draw_badge(draw, 680, y_pos + 6, item["vence_str"], COLOR_BLACK)

            y_pos += 44

        y_pos += 8

    return img


def render_view(view_name: str, data: dict[str, Any], telemetry: dict[str, Any] | None = None) -> Image.Image:
    if view_name == "resumen":
        return render_view_resumen(data, telemetry=telemetry)
    elif view_name == "alta":
        return render_view_list(data, "alta", "2/5", telemetry=telemetry)
    elif view_name == "media":
        return render_view_list(data, "media", "3/5", telemetry=telemetry)
    elif view_name == "baja":
        return render_view_list(data, "baja", "4/5", telemetry=telemetry)
    elif view_name == "clientes":
        return render_view_clientes(data, telemetry=telemetry)
    else:
        return render_view_resumen(data, telemetry=telemetry)


if __name__ == "__main__":
    from data_provider import get_pendientes_data
    d = get_pendientes_data()
    out_dir = Path(__file__).resolve().parent / "previews"
    out_dir.mkdir(exist_ok=True)
    for v in ["resumen", "alta", "media", "baja", "clientes"]:
        pic = render_view(v, d)
        pic_path = out_dir / f"{v}.png"
        pic.save(pic_path)
        print(f"Generado preview {v}: {pic_path}")
