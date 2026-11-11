#!/usr/bin/env python3
"""
generate_cien_anos_tree.py
Lámina 800x480 con el árbol genealógico de los Buendía (Cien años de soledad) para el Spectra 6
del reTerminal E1002.

Sin spoilers: solo nombres y relaciones (matrimonio, unión, adopción, descendencia). Llega hasta
Aureliano Babilonia y no muestra el desenlace. Se dibuja con las 6 tintas exactas y texto sin
antialias, así el driver de ESPHome (que umbraliza, no tramea) no re-mapea ningún píxel.
"""
from __future__ import annotations

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from adapt_gallery_image import PANEL_CODES, PANEL_INKS, _indices, _palette_image, render

WIDTH, HEIGHT = 800, 480
K, W, Y, R = PANEL_CODES[:4]
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / ("DejaVuSerif-Bold.ttf" if bold else "DejaVuSerif.ttf")), size)


# id -> (nombre, generación, x del centro, Buendía de sangre). False = llega a la familia.
PEOPLE = {
    "jab": ("José Arcadio\nBuendía", 1, 330, True),
    "urs": ("Úrsula\nIguarán", 1, 470, True),
    "reb": ("Rebeca", 2, 95, True),
    "ja2": ("José Arcadio", 2, 215, True),
    "pil": ("Pilar\nTernera", 2, 340, False),
    "cor": ("Coronel\nAureliano", 2, 470, True),
    "rmo": ("Remedios\nMoscote", 2, 600, False),
    "ama": ("Amaranta", 2, 725, True),
    "arc": ("Arcadio", 3, 200, True),
    "ssp": ("Santa Sofía\nde la Piedad", 3, 330, False),
    "ajo": ("Aureliano\nJosé", 3, 430, True),
    "a17": ("Los 17\nAurelianos", 3, 600, True),
    "rbe": ("Remedios\nla Bella", 4, 95, True),
    "jas": ("José Arcadio\nSegundo", 4, 215, True),
    "pet": ("Petra\nCotes", 4, 340, False),
    "aus": ("Aureliano\nSegundo", 4, 470, True),
    "fer": ("Fernanda\ndel Carpio", 4, 605, False),
    "mau": ("Mauricio\nBabilonia", 5, 300, False),
    "mem": ("Meme", 5, 430, True),
    "jar": ("José Arcadio", 5, 545, True),
    "amu": ("Amaranta\nÚrsula", 5, 650, True),
    "gas": ("Gastón", 5, 752, False),
    "aub": ("Aureliano\nBabilonia", 6, 365, True),
}
# Parejas vecinas en la misma fila: (izquierda, derecha, tipo).
UNIONS = [
    ("jab", "urs", "matrimonio"), ("reb", "ja2", "matrimonio"), ("ja2", "pil", "union"),
    ("pil", "cor", "union"), ("cor", "rmo", "matrimonio"), ("arc", "ssp", "union"),
    ("pet", "aus", "union"), ("aus", "fer", "matrimonio"), ("mau", "mem", "union"), ("amu", "gas", "matrimonio"),
]
# (padres, hijos). Un solo padre = hijos con mujeres que no aparecen (los 17 Aurelianos).
CHILDREN = [
    (("jab", "urs"), ["reb", "ja2", "cor", "ama"]), (("ja2", "pil"), ["arc"]), (("pil", "cor"), ["ajo"]),
    (("cor",), ["a17"]), (("arc", "ssp"), ["rbe", "jas", "aus"]), (("aus", "fer"), ["mem", "jar", "amu"]),
    (("mau", "mem"), ["aub"]),
]
ADOPTED = {"reb"}
ROW_Y = {g: 92 + (g - 1) * 66 for g in range(1, 7)}
ROMAN = ["I", "II", "III", "IV", "V", "VI"]


def draw_line(draw: ImageDraw.ImageDraw, x1, y1, x2, y2, color=K, width: int = 1, style: str = "solid"):
    """Línea sólida, doble (matrimonio), discontinua (unión) o punteada (adopción)."""
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    if style == "solid":
        draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
        return
    if style == "double":
        off = width + 1
        draw.line([(x1, y1 - off), (x2, y2 - off)], fill=color, width=width)
        draw.line([(x1, y1 + off), (x2, y2 + off)], fill=color, width=width)
        return
    dist = int(math.hypot(x2 - x1, y2 - y1))
    if dist == 0:
        return
    dx, dy = (x2 - x1) / dist, (y2 - y1) / dist
    dash, gap = (6, 4) if style == "dashed" else (1, 3)
    cur = 0
    while cur <= dist:
        end = min(cur + dash, dist)
        draw.line([(x1 + dx * cur, y1 + dy * cur), (x1 + dx * end, y1 + dy * end)], fill=color, width=width)
        cur += dash + gap


def butterfly(draw: ImageDraw.ImageDraw, cx: int, cy: int, s: int, color=Y):
    """Mariposa amarilla con contorno negro (motivo de la novela, sin spoiler)."""
    for side in (-1, 1):
        draw.polygon([(cx, cy), (cx + side * s, cy - s), (cx + side * s * 1.15, cy - s * 0.15)], fill=color, outline=K)
        draw.polygon([(cx, cy), (cx + side * s * 0.85, cy + s * 0.75), (cx + side * s * 0.3, cy + s * 0.85)],
                     fill=color, outline=K)
        draw.line([(cx, cy - s * 0.55), (cx + side * s * 0.35, cy - s * 1.05)], fill=K, width=1)
    draw.line([(cx, cy - s * 0.55), (cx, cy + s * 0.7)], fill=K, width=2)


def text_box(draw, x, y, text, fnt):
    l, t, r, b = draw.multiline_textbbox((x, y), text, font=fnt, anchor="mm", align="center", spacing=1)
    return l, t, r, b


def draw_connectors(draw, boxes: dict, width: int, union_color, bus_drop: int = 33):
    """boxes: id -> (izq, arriba, der, abajo, y_enlace). Dibuja parejas, buses de hijos y bajadas."""
    for a, b, kind in UNIONS:
        y = boxes[a][4]
        draw_line(draw, boxes[a][2] + 3, y, boxes[b][0] - 3, y, union_color if kind == "union" else K, width,
                  "double" if kind == "matrimonio" else "dashed")
    for parents, kids in CHILDREN:
        gen = PEOPLE[parents[0]][1]
        if len(parents) == 2:
            a, b = boxes[parents[0]], boxes[parents[1]]
            sx, sy, bus = (a[2] + b[0]) // 2, a[4], ROW_Y[gen] + bus_drop
        else:  # un solo padre: baja desde su nodo y usa un bus algo más abajo para no fundirse con otro
            p = boxes[parents[0]]
            sx, sy, bus = (p[0] + p[2]) // 2, p[3] + 2, ROW_Y[gen] + bus_drop + 7
        xs = [PEOPLE[k][2] for k in kids]
        draw_line(draw, sx, sy, sx, bus, K, width)
        draw_line(draw, min(xs + [sx]), bus, max(xs + [sx]), bus, K, width)
        for k in kids:
            draw_line(draw, PEOPLE[k][2], bus, PEOPLE[k][2], boxes[k][1] - 2, K, width,
                      "dotted" if k in ADOPTED else "solid")


def draw_line_legend(draw, x: int, y: int, width: int, union_color, fnt) -> None:
    for sample, label, color in (("double", "matrimonio", K), ("dashed", "unión", union_color),
                                 ("dotted", "adopción", K)):
        draw_line(draw, x, y, x + 22, y, color, width, sample)
        draw.text((x + 27, y), label, fill=K, font=fnt, anchor="lm")
        x += 27 + int(draw.textlength(label, font=fnt)) + 16


def draw_poster(draw) -> None:
    """Póster Macondo: marco ornamental, medallones (Buendía de sangre en negro) y mariposas."""
    draw.rectangle((5, 5, WIDTH - 6, HEIGHT - 6), outline=K, width=3)
    draw.rectangle((11, 11, WIDTH - 12, HEIGHT - 12), outline=K, width=1)
    for cx, cy in ((11, 11), (WIDTH - 12, 11), (11, HEIGHT - 12), (WIDTH - 12, HEIGHT - 12)):
        draw.polygon([(cx, cy - 7), (cx + 7, cy), (cx, cy + 7), (cx - 7, cy)], fill=R, outline=K)
    draw.text((WIDTH // 2, 26), "Cien años de soledad", fill=K, font=font(24), anchor="mm")
    draw.text((WIDTH // 2, 49), "— los Buendía de Macondo —", fill=R, font=font(11), anchor="mm")
    for cx, cy, s in ((180, 26, 11), (620, 22, 9), (645, 40, 6), (40, 440, 9), (60, 455, 6), (760, 60, 7)):
        butterfly(draw, cx, cy, s)
    boxes = {}
    fnt = font(11)
    for pid, (name, gen, x, blood) in PEOPLE.items():
        cy = ROW_Y[gen] - 13
        draw.ellipse((x - 7, cy - 7, x + 7, cy + 7), fill=K if blood else W, outline=K, width=2)
        if blood:
            draw.ellipse((x - 2, cy - 2, x + 2, cy + 2), fill=Y)
        draw.multiline_text((x, ROW_Y[gen] + 7), name, fill=K, font=fnt, anchor="mm", align="center", spacing=0)
        _, _, _, b = text_box(draw, x, ROW_Y[gen] + 7, name, fnt)
        boxes[pid] = (x - 8, cy - 8, x + 8, b, cy)
    draw_connectors(draw, boxes, 2, R, bus_drop=31)
    for g, y in ROW_Y.items():
        draw.text((32, y - 6), ROMAN[g - 1], fill=R, font=font(13), anchor="mm")
    small = font(11, bold=False)
    draw_line_legend(draw, 492, 446, 2, R, small)
    draw.ellipse((492, 420, 504, 432), fill=K, outline=K)
    draw.ellipse((496, 424, 500, 428), fill=Y)
    draw.text((510, 426), "Buendía", fill=K, font=small, anchor="lm")
    draw.ellipse((580, 420, 592, 432), fill=W, outline=K, width=2)
    draw.text((598, 426), "llegan a la familia", fill=K, font=small, anchor="lm")


def generate_tree_image(output_path: Path, preview_path: Path | None = None) -> Image.Image:
    im = Image.new("RGB", (WIDTH, HEIGHT), W)
    draw = ImageDraw.Draw(im)
    draw.fontmode = "1"  # sin antialias: solo tintas puras, nada que el driver tenga que re-mapear
    draw_poster(draw)
    indices = _indices(im.quantize(palette=_palette_image(PANEL_CODES), dither=Image.Dither.NONE))
    out = render(indices, PANEL_CODES)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(output_path, format="PNG", optimize=True)
    if preview_path:
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        render(indices, PANEL_INKS).save(preview_path, format="PNG", optimize=True)
    return out


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    out = here / "gallery" / "99_cien_anos_arbol.png"
    generate_tree_image(out, here / "previews" / "cien_anos_arbol.png")
    print(f"Árbol genealógico generado en: {out}")
