#!/usr/bin/env python3
"""
generate_cien_anos_tree.py
Genera una lámina gráfica panorámica (800x480 px) con el ÁRBOL GENEALÓGICO
de la familia Buendía (Cien años de soledad), diseñado con estilo de diagrama
genealógico visual, optimizado para la pantalla ePaper Spectra 6 del reTerminal E1002:
- Sin footer negro inferior (aprovecha los 480 px de altura completos).
- Tipografía BOLD grande (10-15 px) con máximo contraste.
- Cajas con contorno sólido de 2 px y franjas de color saturadas.
- Conectores gruesos (2-3 px): dobles para matrimonio, discontinuos rojos para romance.
- Estrictamente SIN SPOILERS.
"""
from __future__ import annotations

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Dimensiones exactas pantalla reTerminal E1002
WIDTH = 800
HEIGHT = 480

# Paleta oficial Spectra 6 de alto contraste
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_RED = (220, 38, 38)
COLOR_BLUE = (30, 58, 138)
COLOR_GREEN = (22, 101, 52)
COLOR_AMBER = (180, 83, 9)
COLOR_SLATE = (30, 41, 59)
COLOR_CRIMSON = (153, 27, 27)

FONT_PATH_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def get_font(size: float) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_PATH_BOLD, int(size))
    except Exception:
        return ImageFont.load_default()


F_HEADER_TITLE = get_font(14)
F_HEADER_LEGEND = get_font(11)
F_GEN = get_font(11)
F_NAME_LARGE = get_font(12)
F_NAME = get_font(11)
F_NAME_SMALL = get_font(10)
F_TRAIT_LARGE = get_font(11)
F_TRAIT = get_font(10)


def draw_line(
    draw: ImageDraw.ImageDraw,
    x1: int | float,
    y1: int | float,
    x2: int | float,
    y2: int | float,
    color: tuple = COLOR_BLACK,
    width: int = 2,
    style: str = "solid",
):
    """Dibuja líneas gruesas de alto contraste (sólida, doble o discontinua)."""
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    if style == "solid":
        draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    elif style == "double":
        # Matrimonio: dos líneas paralelas de 2px
        if y1 == y2:
            draw.line([(x1, y1 - 2), (x2, y2 - 2)], fill=color, width=width)
            draw.line([(x1, y1 + 2), (x2, y2 + 2)], fill=color, width=width)
        else:
            draw.line([(x1 - 2, y1), (x2 - 2, y2)], fill=color, width=width)
            draw.line([(x1 + 2, y1), (x2 + 2, y2)], fill=color, width=width)
    elif style == "dashed":
        # Romance / Pareja: línea discontinua de alto contraste
        dist = int(math.hypot(x2 - x1, y2 - y1))
        if dist == 0:
            return
        dx = (x2 - x1) / dist
        dy = (y2 - y1) / dist
        dash_len = 7
        gap_len = 4
        cur = 0
        while cur < dist:
            seg_end = min(cur + dash_len, dist)
            draw.line(
                [(x1 + dx * cur, y1 + dy * cur), (x1 + dx * seg_end, y1 + dy * seg_end)],
                fill=color,
                width=width,
            )
            cur += dash_len + gap_len
    elif style == "dotted":
        # Adopción: puntos gruesos
        dist = int(math.hypot(x2 - x1, y2 - y1))
        if dist == 0:
            return
        dx = (x2 - x1) / dist
        dy = (y2 - y1) / dist
        cur = 0
        while cur <= dist:
            px, py = int(x1 + dx * cur), int(y1 + dy * cur)
            draw.rectangle((px - 1, py - 1, px + 1, py + 1), fill=color)
            cur += 5


def draw_card(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    name: str,
    trait: str,
    header_col: tuple = COLOR_BLUE,
):
    """Dibuja una ficha de personaje nítida con contorno negro de 2px y texto BOLD."""
    x, y, w, h = int(x), int(y), int(w), int(h)
    hbar_h = 20

    # Fondo blanco puro y contorno exterior de 2px negro
    draw.rectangle((x, y, x + w, y + h), fill=COLOR_WHITE, outline=COLOR_BLACK, width=2)
    # Franja superior coloreada
    draw.rectangle((x + 1, y + 1, x + w - 1, y + hbar_h), fill=header_col)
    draw.line([(x, y + hbar_h), (x + w, y + hbar_h)], fill=COLOR_BLACK, width=1)

    # Nombre en negrita blanco puro
    fn = F_NAME
    if fn.getlength(name) > (w - 8):
        fn = F_NAME_SMALL
    draw.text((x + 5, y + 3), name, fill=COLOR_WHITE, font=fn)

    # Rasgo / símbolo en negrita negro puro sobre fondo blanco
    draw.text((x + 5, y + 23), trait, fill=COLOR_BLACK, font=F_TRAIT)


def draw_large_card(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    name: str,
    lines: list[str],
    header_col: tuple = COLOR_CRIMSON,
):
    """Dibuja una ficha amplia para las generaciones finales con múltiples líneas."""
    x, y, w, h = int(x), int(y), int(w), int(h)
    hbar_h = 22

    # Fondo blanco puro y contorno exterior de 2px negro
    draw.rectangle((x, y, x + w, y + h), fill=COLOR_WHITE, outline=COLOR_BLACK, width=2)
    # Franja de cabecera
    draw.rectangle((x + 1, y + 1, x + w - 1, y + hbar_h), fill=header_col)
    draw.line([(x, y + hbar_h), (x + w, y + hbar_h)], fill=COLOR_BLACK, width=1)

    # Nombre
    draw.text((x + 6, y + 3), name, fill=COLOR_WHITE, font=F_NAME_LARGE)

    # Líneas de descripción en negrita
    cur_y = y + 26
    for line in lines:
        draw.text((x + 6, cur_y), line, fill=COLOR_BLACK, font=F_TRAIT_LARGE)
        cur_y += 18


def generate_tree_image(output_path: Path) -> Image.Image:
    im = Image.new("RGB", (WIDTH, HEIGHT), COLOR_WHITE)
    draw = ImageDraw.Draw(im)

    # =========================================================================
    # 1. CABECERA PANORÁMICA (Y: 0 a 28) CON LEYENDA INTEGRADA
    # =========================================================================
    draw.rectangle((0, 0, WIDTH, 28), fill=COLOR_BLUE)
    draw.text(
        (10, 6),
        "ÁRBOL GENEALÓGICO DE LA FAMILIA BUENDÍA  •  MACONDO",
        fill=COLOR_WHITE,
        font=F_HEADER_TITLE,
    )

    # Leyenda compacta en la cabecera (sin ocupar espacio inferior)
    draw.text(
        (545, 7),
        "═ Matrimonio   ┅ Romance   ··· Adopción",
        fill=(254, 240, 138),
        font=F_HEADER_LEGEND,
    )
    draw.line([(0, 28), (WIDTH, 28)], fill=COLOR_BLACK, width=1)

    # =========================================================================
    # 2. COLUMNA LATERAL DE GENERACIONES (X: 4 a 46)
    # =========================================================================
    gen_bands = [
        ("1ª Gen", 34, 40, COLOR_BLUE),
        ("2ª Gen", 98, 40, COLOR_GREEN),
        ("3ª Gen", 164, 40, COLOR_AMBER),
        ("4ª Gen", 230, 40, COLOR_RED),
        ("5ª Gen", 296, 40, COLOR_SLATE),
        ("6ª-7ª", 368, 96, COLOR_CRIMSON),
    ]
    for tag, y_pos, h_box, col in gen_bands:
        draw.rectangle((4, y_pos, 46, y_pos + h_box), fill=col, outline=COLOR_BLACK, width=2)
        w_t = F_GEN.getlength(tag)
        draw.text((4 + (42 - w_t) / 2, y_pos + (h_box - 14) / 2), tag, fill=COLOR_WHITE, font=F_GEN)

    # =========================================================================
    # NIVEL 1: 1ª GENERACIÓN (FUNDADORES) - Y: 34 a 74 (H=40)
    # =========================================================================
    draw_card(draw, 200, 34, 185, 40, "José Arcadio Buendía", "Fundador de Macondo", COLOR_BLUE)
    draw_card(draw, 445, 34, 165, 40, "Úrsula Iguarán", "Matriarca laboriosa", COLOR_BLUE)

    # Enlace matrimonial José Arcadio Buendía ══ Úrsula Iguarán
    draw_line(draw, 385, 54, 445, 54, width=2, style="double")

    # Tronco de descendencia Gen 1 -> Gen 2
    draw_line(draw, 415, 54, 415, 86, width=2, style="solid")
    draw_line(draw, 105, 86, 760, 86, width=2, style="solid")
    # Ramas hacia Gen 2
    draw_line(draw, 105, 86, 105, 98, width=2, style="dotted")  # Rebeca (adopción)
    draw_line(draw, 245, 86, 245, 98, width=2, style="solid")   # José Arcadio
    draw_line(draw, 545, 86, 545, 98, width=2, style="solid")   # Coronel Aureliano
    draw_line(draw, 760, 86, 760, 98, width=2, style="solid")   # Amaranta

    # =========================================================================
    # NIVEL 2: 2ª GENERACIÓN (HIJOS Y PAREJAS) - Y: 98 a 138 (H=40)
    # =========================================================================
    draw_card(draw, 55, 98, 100, 40, "Rebeca", "Adoptiva", COLOR_GREEN)
    draw_card(draw, 175, 98, 145, 40, "José Arcadio", "Fuerza colosal", COLOR_GREEN)
    draw_card(draw, 340, 98, 115, 40, "Pilar Ternera", "Cartomántica", COLOR_AMBER)
    draw_card(draw, 475, 98, 150, 40, "Cnel. Aureliano", "Pescaditos de oro", COLOR_GREEN)
    draw_card(draw, 645, 98, 75, 40, "Remedios", "Moscote", COLOR_GREEN)
    draw_card(draw, 730, 98, 65, 40, "Amaranta", "Costura", COLOR_GREEN)

    # Conexiones Gen 2
    draw_line(draw, 155, 118, 175, 118, width=2, style="double")  # Rebeca ══ José Arcadio
    draw_line(draw, 320, 118, 340, 118, color=COLOR_RED, width=2, style="dashed")  # José Arcadio ┅ Pilar Ternera
    draw_line(draw, 455, 118, 475, 118, color=COLOR_RED, width=2, style="dashed")  # Pilar Ternera ┅ Cnel. Aureliano
    draw_line(draw, 625, 118, 645, 118, width=2, style="double")  # Cnel. Aureliano ══ Remedios Moscote

    # Troncos de descendencia Gen 2 -> Gen 3
    # 1. José Arcadio + Pilar Ternera -> Arcadio
    draw_line(draw, 330, 118, 330, 151, width=2, style="solid")
    draw_line(draw, 145, 151, 330, 151, width=2, style="solid")
    draw_line(draw, 145, 151, 145, 164, width=2, style="solid")

    # 2. Coronel Aureliano + Pilar Ternera -> Aureliano José
    draw_line(draw, 465, 118, 465, 151, width=2, style="solid")
    draw_line(draw, 465, 151, 490, 151, width=2, style="solid")
    draw_line(draw, 490, 151, 490, 164, width=2, style="solid")

    # 3. Coronel Aureliano (campañas) -> Los 17 Aurelianos
    draw_line(draw, 580, 138, 580, 151, width=2, style="solid")
    draw_line(draw, 580, 151, 690, 151, width=2, style="solid")
    draw_line(draw, 690, 151, 690, 164, width=2, style="solid")

    # =========================================================================
    # NIVEL 3: 3ª GENERACIÓN (NIETOS) - Y: 164 a 204 (H=40)
    # =========================================================================
    draw_card(draw, 80, 164, 125, 40, "Arcadio", "Gobernador", COLOR_AMBER)
    draw_card(draw, 225, 164, 155, 40, "Santa Sofía Piedad", "Madre abnegada", COLOR_AMBER)
    draw_card(draw, 420, 164, 145, 40, "Aureliano José", "Soldado rebelde", COLOR_AMBER)
    draw_card(draw, 595, 164, 195, 40, "Los 17 Aurelianos", "Cruz de ceniza", COLOR_AMBER)

    # Conexión Arcadio ══ Santa Sofía
    draw_line(draw, 205, 184, 225, 184, width=2, style="double")

    # Tronco Gen 3 -> Gen 4 (Hijos de Arcadio + Santa Sofía de la Piedad)
    draw_line(draw, 215, 184, 215, 217, width=2, style="solid")
    draw_line(draw, 135, 217, 460, 217, width=2, style="solid")
    draw_line(draw, 135, 217, 135, 230, width=2, style="solid")  # Remedios la Bella
    draw_line(draw, 300, 217, 300, 230, width=2, style="solid")  # José Arcadio Segundo
    draw_line(draw, 460, 217, 460, 230, width=2, style="solid")  # Aureliano Segundo

    # =========================================================================
    # NIVEL 4: 4ª GENERACIÓN (BISNIETOS) - Y: 230 a 270 (H=40)
    # =========================================================================
    draw_card(draw, 60, 230, 150, 40, "Remedios la Bella", "Belleza celestial", COLOR_RED)
    draw_card(draw, 225, 230, 150, 40, "José Arcadio 2º", "Gemelo • Gallos", COLOR_RED)
    draw_card(draw, 390, 230, 140, 40, "Aureliano 2º", "Gemelo • Acordeón", COLOR_RED)
    draw_card(draw, 550, 230, 145, 40, "Fernanda Carpio", "Reina devota", COLOR_RED)
    draw_card(draw, 710, 230, 85, 40, "Petra Cotes", "Ganado fértil", COLOR_RED)

    # Conexiones Gen 4
    draw_line(draw, 530, 250, 550, 250, width=2, style="double")  # Aureliano 2º ══ Fernanda
    draw_line(draw, 695, 250, 710, 250, color=COLOR_RED, width=2, style="dashed")  # Aureliano 2º ┅ Petra Cotes

    # Tronco Gen 4 -> Gen 5 (Hijos de Aureliano 2º + Fernanda)
    draw_line(draw, 540, 250, 540, 283, width=2, style="solid")
    draw_line(draw, 135, 283, 645, 283, width=2, style="solid")
    draw_line(draw, 135, 283, 135, 296, width=2, style="solid")  # José Arcadio
    draw_line(draw, 295, 283, 295, 296, width=2, style="solid")  # Renata (Meme)
    draw_line(draw, 645, 283, 645, 296, width=2, style="solid")  # Amaranta Úrsula

    # =========================================================================
    # NIVEL 5: 5ª GENERACIÓN (TATARANIETOS) - Y: 296 a 336 (H=40)
    # =========================================================================
    draw_card(draw, 65, 296, 145, 40, "José Arcadio (Roma)", "Estudios en Roma", COLOR_SLATE)
    draw_card(draw, 225, 296, 145, 40, "Renata (Meme)", "Clavicordio", COLOR_SLATE)
    draw_card(draw, 390, 296, 160, 40, "Mauricio Babilonia", "Mariposas amarillas", COLOR_AMBER)
    draw_card(draw, 575, 296, 145, 40, "Amaranta Úrsula", "Enérgica y vital", COLOR_SLATE)
    draw_card(draw, 735, 296, 60, 40, "Gastón", "Aviador", COLOR_SLATE)

    # Conexiones Gen 5
    draw_line(draw, 370, 316, 390, 316, color=COLOR_RED, width=2, style="dashed")  # Meme ┅ Mauricio Babilonia
    draw_line(draw, 720, 316, 735, 316, width=2, style="double")  # Amaranta Úrsula ══ Gastón

    # Tronco Gen 5 -> Gen 6 (Meme + Mauricio Babilonia -> Aureliano Babilonia)
    draw_line(draw, 380, 316, 380, 350, width=2, style="solid")
    draw_line(draw, 280, 350, 380, 350, width=2, style="solid")
    draw_line(draw, 280, 350, 280, 368, width=2, style="solid")

    # =========================================================================
    # NIVEL 6 Y 7: 6ª Y 7ª GENERACIÓN (FIN DEL LINAJE) - Y: 368 a 468 (H=96)
    # =========================================================================
    draw_large_card(
        draw,
        x=140,
        y=368,
        w=295,
        h=96,
        name="Aureliano Babilonia (6ª Gen)",
        lines=[
            "• Sabio ermitaño y lector incansable",
            "• Descifra los pergaminos de Melquíades",
            "• Gran amor con Amaranta Úrsula",
        ],
        header_col=COLOR_CRIMSON,
    )

    draw_large_card(
        draw,
        x=495,
        y=368,
        w=295,
        h=96,
        name="El Último Aureliano (7ª Gen)",
        lines=[
            "• Hijo de la estirpe y fin del linaje",
            "• El niño con cola de cerdo",
            "• Clausura de los cien años de soledad",
        ],
        header_col=COLOR_BLACK,
    )

    # Conexión Amaranta Úrsula (Gen 5) hacia el linaje final
    draw_line(draw, 645, 336, 645, 355, width=2, style="solid")
    draw_line(draw, 465, 355, 645, 355, width=2, style="solid")
    draw_line(draw, 465, 355, 465, 416, width=2, style="solid")

    # Enlace de amor entre Aureliano Babilonia y Amaranta Úrsula hacia El Último Aureliano
    draw_line(draw, 435, 416, 495, 416, color=COLOR_RED, width=2, style="dashed")

    # Guardar imagen optimizada para Spectra 6 (< 60 KB para buffer ESPHome)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    im_opt = im.quantize(colors=16)
    im_opt.save(output_path, format="PNG", optimize=True)
    return im_opt


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "gallery" / "99_cien_anos_arbol.png"
    generate_tree_image(out)
    prev = Path(__file__).resolve().parent / "previews" / "cien_anos_arbol.png"
    generate_tree_image(prev)
    print(f"Lámina del árbol rediseñada y guardada en: {out}")
