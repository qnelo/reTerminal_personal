#!/usr/bin/env python3
"""
generate_cien_anos_tree.py
Genera una lámina gráfica panorámica (800x480 px) con el ÁRBOL GENEALÓGICO
de la familia Buendía (Cien años de soledad), diseñado con estilo de diagrama
genealógico visual (cajas de personajes, enlaces matrimoniales y ramas de
descendencia por generaciones), optimizado para la pantalla ePaper Spectra 6
del reTerminal E1002 y estrictamente SIN SPOILERS.
"""
from __future__ import annotations

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# Dimensiones exactas pantalla reTerminal E1002
WIDTH = 800
HEIGHT = 480

# Paleta oficial Spectra 6
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_DARK_GRAY = (31, 41, 55)
COLOR_LIGHT_GRAY = (243, 244, 246)
COLOR_CARD_BORDER = (156, 163, 175)
COLOR_LINE = (75, 85, 99)
COLOR_BLUE = (30, 58, 138)
COLOR_LIGHT_BLUE = (219, 234, 254)
COLOR_RED = (185, 28, 28)
COLOR_LIGHT_RED = (254, 226, 226)
COLOR_AMBER = (180, 83, 9)
COLOR_LIGHT_AMBER = (254, 243, 199)
COLOR_GREEN = (22, 101, 52)
COLOR_LIGHT_GREEN = (220, 252, 231)
COLOR_YELLOW = (202, 138, 4)
COLOR_LIGHT_YELLOW = (254, 240, 138)

FONT_PATH_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_PATH_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    path = FONT_PATH_BOLD if bold else FONT_PATH_REG
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

F_HEADER_TITLE = get_font(13, bold=True)
F_HEADER_SUB = get_font(9, bold=True)
F_GEN_TAG = get_font(8, bold=True)
F_NAME = get_font(9, bold=True)
F_SUB = get_font(7, bold=False)
F_LEGEND = get_font(8, bold=True)


def draw_node(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    name: str,
    sub: str,
    accent_color: tuple = COLOR_BLUE,
    bg_color: tuple = COLOR_WHITE,
    border_color: tuple = COLOR_CARD_BORDER,
):
    """Dibuja una caja de personaje con marco y acento."""
    draw.rounded_rectangle((x, y, x + w, y + h), radius=3, fill=bg_color, outline=border_color, width=1)
    # Franja de color superior o lateral
    draw.rounded_rectangle((x, y, x + 3, y + h), radius=1, fill=accent_color)
    # Nombre
    draw.text((x + 6, y + 3), name, fill=COLOR_BLACK, font=F_NAME)
    # Subtítulo (rasgo sin spoiler)
    draw.text((x + 6, y + 17), sub, fill=COLOR_DARK_GRAY, font=F_SUB)


def draw_h_line(draw: ImageDraw.ImageDraw, x1: int, x2: int, y: int, color: tuple = COLOR_LINE, width: int = 1, dashed: bool = False, dotted: bool = False):
    x_start, x_end = min(x1, x2), max(x1, x2)
    if dotted:
        for x in range(x_start, x_end, 5):
            draw.point((x, y), fill=color)
    elif dashed:
        for x in range(x_start, x_end, 7):
            draw.line([(x, y), (min(x + 4, x_end), y)], fill=color, width=width)
    else:
        draw.line([(x_start, y), (x_end, y)], fill=color, width=width)


def draw_v_line(draw: ImageDraw.ImageDraw, x: int, y1: int, y2: int, color: tuple = COLOR_LINE, width: int = 1, dashed: bool = False, dotted: bool = False):
    y_start, y_end = min(y1, y2), max(y1, y2)
    if dotted:
        for y in range(y_start, y_end, 5):
            draw.point((x, y), fill=color)
    elif dashed:
        for y in range(y_start, y_end, 7):
            draw.line([(x, y), (x, min(y + 4, y_end))], fill=color, width=width)
    else:
        draw.line([(x, y_start), (x, y_end)], fill=color, width=width)


def draw_couple_link(draw: ImageDraw.ImageDraw, x1: int, x2: int, y: int, style: str = "marriage"):
    """Dibuja el conector de pareja (doble línea para matrimonio o discontinua para romance)."""
    if style == "marriage":
        draw_h_line(draw, x1, x2, y - 2, color=COLOR_LINE, width=1)
        draw_h_line(draw, x1, x2, y + 2, color=COLOR_LINE, width=1)
    else:
        draw_h_line(draw, x1, x2, y, color=COLOR_LINE, width=1, dashed=True)


def generate_tree_image(output_path: Path) -> Image.Image:
    im = Image.new("RGB", (WIDTH, HEIGHT), COLOR_WHITE)
    draw = ImageDraw.Draw(im)

    # ==========================================
    # 1. CABECERA COMPACTA (Y: 0 a 28)
    # ==========================================
    draw.rectangle((0, 0, WIDTH, 28), fill=COLOR_BLUE)
    draw.text((10, 7), "ÁRBOL GENEALÓGICO DE LA FAMILIA BUENDÍA  •  CIEN AÑOS DE SOLEDAD", fill=COLOR_WHITE, font=F_HEADER_TITLE)
    draw.text((585, 9), "Guía genealógica de lectura", fill=(253, 230, 138), font=F_HEADER_SUB)

    # ==========================================
    # 2. PIE DE PÁGINA (Y: 458 a 480)
    # ==========================================
    draw.rectangle((0, 458, WIDTH, 480), fill=COLOR_BLACK)
    legend = "═ Matrimonio   - - Romance   ··· Adopción  |  ◄ / ►: Galería (1/2)  |  Ambos botones: Pendientes"
    draw.text((12, 463), legend, fill=COLOR_WHITE, font=F_LEGEND)
    draw.text((715, 463), "reTerminal E1002", fill=(156, 163, 175), font=F_LEGEND)

    # ==========================================
    # 3. ETIQUETAS LATERALES DE GENERACIÓN
    # ==========================================
    gen_tags = [
        ("1ª Gen", 34, 30, COLOR_BLUE),
        ("2ª Gen", 102, 32, COLOR_GREEN),
        ("3ª Gen", 172, 32, COLOR_AMBER),
        ("4ª Gen", 244, 32, COLOR_RED),
        ("5ª Gen", 318, 32, COLOR_YELLOW),
        ("6ª-7ª", 392, 44, COLOR_DARK_GRAY),
    ]
    for text, y_pos, h_box, col in gen_tags:
        draw.rounded_rectangle((6, y_pos, 46, y_pos + h_box), radius=2, fill=col)
        draw.text((10, y_pos + h_box // 2 - 5), text, fill=COLOR_WHITE, font=F_GEN_TAG)

    # =========================================================================
    # NIVEL 1: 1ª GENERACIÓN (FUNDADORES) - Y: 34 a 64
    # =========================================================================
    # José Arcadio Buendía
    draw_node(draw, 220, 34, 165, 30, "José Arcadio Buendía", "Fundador de Macondo • Soñador", COLOR_BLUE, COLOR_LIGHT_BLUE)
    # Úrsula Iguarán
    draw_node(draw, 455, 34, 165, 30, "Úrsula Iguarán", "Matriarca del hogar • Laboriosa", COLOR_BLUE, COLOR_LIGHT_BLUE)
    # Enlace matrimonial
    draw_couple_link(draw, 385, 455, 49, "marriage")

    # Tronco de descendencia Gen 1 -> Gen 2
    draw_v_line(draw, 420, 49, 84, COLOR_LINE, width=1)
    # Barra horizontal de distribución a los 4 hijos
    draw_h_line(draw, 115, 750, 84, COLOR_LINE, width=1)
    # Ramas hacia Gen 2
    draw_v_line(draw, 115, 84, 102, COLOR_LINE, width=1, dotted=True) # Rebeca (adopción)
    draw_v_line(draw, 255, 84, 102, COLOR_LINE, width=1)              # José Arcadio
    draw_v_line(draw, 530, 84, 102, COLOR_LINE, width=1)              # Coronel Aureliano
    draw_v_line(draw, 750, 84, 102, COLOR_LINE, width=1)              # Amaranta

    # =========================================================================
    # NIVEL 2: 2ª GENERACIÓN (HIJOS Y PAREJAS) - Y: 102 a 134
    # =========================================================================
    # Rebeca (adoptiva)
    draw_node(draw, 56, 102, 120, 32, "Rebeca", "Adoptiva • Come tierra", COLOR_GREEN, COLOR_LIGHT_GREEN)
    # Conexión Rebeca = José Arcadio (matrimonio posterior)
    draw_couple_link(draw, 176, 192, 118, "marriage")

    # José Arcadio
    draw_node(draw, 192, 102, 130, 32, "José Arcadio", "Primogénito • Fuerza colosal", COLOR_GREEN, COLOR_LIGHT_GREEN)
    # Romance con Pilar Ternera
    draw_couple_link(draw, 322, 340, 118, "romance")

    # Pilar Ternera
    draw_node(draw, 340, 102, 95, 32, "Pilar Ternera", "Cartomántica alegre", COLOR_AMBER, COLOR_LIGHT_AMBER)
    # Romance con Coronel Aureliano
    draw_couple_link(draw, 435, 455, 118, "romance")

    # Coronel Aureliano Buendía
    draw_node(draw, 455, 102, 155, 32, "Cnel. Aureliano Buendía", "Clarividente • Pescaditos oro", COLOR_GREEN, COLOR_LIGHT_GREEN)
    # Matrimonio con Remedios Moscote
    draw_couple_link(draw, 610, 626, 118, "marriage")

    # Remedios Moscote
    draw_node(draw, 626, 102, 80, 32, "Remedios M.", "Niña dulce y pura", COLOR_GREEN, COLOR_WHITE)

    # Amaranta
    draw_node(draw, 714, 102, 78, 32, "Amaranta", "Costura fina", COLOR_GREEN, COLOR_LIGHT_GREEN)

    # Troncos de descendencia Gen 2 -> Gen 3
    # 1. José Arcadio + Pilar Ternera -> Arcadio
    draw_v_line(draw, 331, 118, 154, COLOR_LINE, width=1)
    draw_h_line(draw, 172, 331, 154, COLOR_LINE, width=1)
    draw_v_line(draw, 172, 154, 172, COLOR_LINE, width=1)

    # 2. Coronel Aureliano + Pilar Ternera -> Aureliano José
    draw_v_line(draw, 445, 118, 154, COLOR_LINE, width=1)
    draw_h_line(draw, 445, 480, 154, COLOR_LINE, width=1)
    draw_v_line(draw, 480, 154, 172, COLOR_LINE, width=1)

    # 3. Coronel Aureliano (campañas) -> Los 17 Aurelianos
    draw_v_line(draw, 570, 134, 154, COLOR_LINE, width=1)
    draw_h_line(draw, 570, 680, 154, COLOR_LINE, width=1)
    draw_v_line(draw, 680, 154, 172, COLOR_LINE, width=1)

    # =========================================================================
    # NIVEL 3: 3ª GENERACIÓN (NIETOS) - Y: 172 a 204
    # =========================================================================
    # Arcadio
    draw_node(draw, 110, 172, 125, 32, "Arcadio", "Maestro • Gobernador", COLOR_AMBER, COLOR_LIGHT_AMBER)
    # Matrimonio/Unión con Santa Sofía de la Piedad
    draw_couple_link(draw, 235, 252, 188, "marriage")

    # Santa Sofía de la Piedad
    draw_node(draw, 252, 172, 125, 32, "Santa Sofía Piedad", "Silenciosa y abnegada", COLOR_AMBER, COLOR_WHITE)

    # Aureliano José
    draw_node(draw, 412, 172, 135, 32, "Aureliano José", "Criado por Amaranta • Soldado", COLOR_AMBER, COLOR_LIGHT_AMBER)

    # Los 17 Aurelianos
    draw_node(draw, 585, 172, 195, 32, "Los 17 Aurelianos", "Hijos de campaña • Cruz ceniza", COLOR_AMBER, COLOR_LIGHT_AMBER)

    # Tronco de descendencia Gen 3 -> Gen 4 (Hijos de Arcadio + Santa Sofía)
    mid_arcadio = 243
    draw_v_line(draw, mid_arcadio, 188, 226, COLOR_LINE, width=1)
    draw_h_line(draw, 125, 445, 226, COLOR_LINE, width=1)
    draw_v_line(draw, 125, 226, 244, COLOR_LINE, width=1) # Remedios la Bella
    draw_v_line(draw, 285, 226, 244, COLOR_LINE, width=1) # José Arcadio Segundo
    draw_v_line(draw, 445, 226, 244, COLOR_LINE, width=1) # Aureliano Segundo

    # =========================================================================
    # NIVEL 4: 4ª GENERACIÓN (BISNIETOS) - Y: 244 a 276
    # =========================================================================
    # Remedios la Bella
    draw_node(draw, 56, 244, 140, 32, "Remedios la Bella", "Belleza etérea • Inocente", COLOR_RED, COLOR_LIGHT_RED)

    # José Arcadio Segundo
    draw_node(draw, 210, 244, 150, 32, "José Arcadio 2º", "Gemelo • Gallos y barcos", COLOR_RED, COLOR_LIGHT_RED)

    # Aureliano Segundo
    draw_node(draw, 370, 244, 150, 32, "Aureliano 2º", "Gemelo • Toca acordeón", COLOR_RED, COLOR_LIGHT_RED)
    # Matrimonio con Fernanda del Carpio
    draw_couple_link(draw, 520, 538, 260, "marriage")

    # Fernanda del Carpio
    draw_node(draw, 538, 244, 135, 32, "Fernanda del Carpio", "Educada para reina • Devota", COLOR_RED, COLOR_WHITE)
    # Romance con Petra Cotes
    draw_couple_link(draw, 673, 690, 260, "romance")

    # Petra Cotes
    draw_node(draw, 690, 244, 102, 32, "Petra Cotes", "Ganado fértil", COLOR_RED, COLOR_WHITE)

    # Tronco de descendencia Gen 4 -> Gen 5 (Hijos de Aureliano Segundo + Fernanda)
    mid_aureliano2 = 529
    draw_v_line(draw, mid_aureliano2, 260, 300, COLOR_LINE, width=1)
    draw_h_line(draw, 145, 645, 300, COLOR_LINE, width=1)
    draw_v_line(draw, 145, 300, 318, COLOR_LINE, width=1) # José Arcadio
    draw_v_line(draw, 295, 300, 318, COLOR_LINE, width=1) # Renata (Meme)
    draw_v_line(draw, 645, 300, 318, COLOR_LINE, width=1) # Amaranta Úrsula

    # =========================================================================
    # NIVEL 5: 5ª GENERACIÓN (TATARANIETOS) - Y: 318 a 350
    # =========================================================================
    # José Arcadio
    draw_node(draw, 75, 318, 140, 32, "José Arcadio", "Seminario en Roma", COLOR_DARK_GRAY, COLOR_LIGHT_GRAY)

    # Renata Remedios (Meme)
    draw_node(draw, 225, 318, 140, 32, "Renata (Meme)", "Clavicordio • Rebelde", COLOR_DARK_GRAY, COLOR_LIGHT_GRAY)
    # Romance con Mauricio Babilonia
    draw_couple_link(draw, 365, 382, 334, "romance")

    # Mauricio Babilonia
    draw_node(draw, 382, 318, 155, 32, "Mauricio Babilonia", "Mariposas amarillas", COLOR_YELLOW, COLOR_LIGHT_YELLOW)

    # Amaranta Úrsula
    draw_node(draw, 570, 318, 145, 32, "Amaranta Úrsula", "Enérgica • Europa", COLOR_DARK_GRAY, COLOR_LIGHT_GRAY)
    # Matrimonio con Gastón
    draw_couple_link(draw, 715, 730, 334, "marriage")

    # Gastón
    draw_node(draw, 730, 318, 62, 32, "Gastón", "Aviador", COLOR_DARK_GRAY, COLOR_WHITE)

    # Tronco Gen 5 -> Gen 6: Meme + Mauricio Babilonia -> Aureliano Babilonia
    mid_meme = 373
    draw_v_line(draw, mid_meme, 334, 372, COLOR_LINE, width=1)
    draw_h_line(draw, mid_meme, 360, 372, COLOR_LINE, width=1)
    draw_v_line(draw, 360, 372, 392, COLOR_LINE, width=1)

    # =========================================================================
    # NIVEL 6 Y 7: 6ª Y 7ª GENERACIÓN (FIN DEL LINAJE) - Y: 392 a 438
    # =========================================================================
    # Aureliano Babilonia (6ª Gen)
    draw_node(draw, 260, 392, 195, 42, "Aureliano Babilonia (6ª)", "Sabio ermitaño • Lector de manuscritos\nDescifra pergaminos de Melquíades", COLOR_BLUE, COLOR_LIGHT_BLUE)

    # Conexión entre Amaranta Úrsula y Aureliano Babilonia
    draw_v_line(draw, 642, 350, 372, COLOR_LINE, width=1)
    draw_h_line(draw, 455, 642, 372, COLOR_LINE, width=1)
    draw_v_line(draw, 520, 372, 412, COLOR_LINE, width=1)

    # Conector hacia El Último Aureliano
    draw_h_line(draw, 455, 520, 412, COLOR_LINE, width=1)
    draw_couple_link(draw, 455, 535, 412, "romance")

    # El Último Aureliano (7ª Gen)
    draw_node(draw, 535, 392, 235, 42, "El Último Aureliano (7ª)", "Hijo de Amaranta Úrsula • Final del linaje\nCierre de la estirpe de los Buendía", COLOR_RED, COLOR_LIGHT_RED)

    # Guardar imagen optimizada para Spectra 6 (< 60 KB para buffer ESPHome)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    im_opt = im.quantize(colors=16)
    im_opt.save(output_path, format="PNG", optimize=True)
    return im_opt


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "gallery" / "01_cien_anos_arbol.png"
    generate_tree_image(out)
    # También actualizar preview
    prev = Path(__file__).resolve().parent / "previews" / "cien_anos_arbol.png"
    generate_tree_image(prev)
    print(f"Lámina del árbol estilo organigrama genealógico generada en: {out}")
