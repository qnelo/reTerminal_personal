#!/usr/bin/env python3
"""
adapt_gallery_image.py
Adapta una fotografía para la pantalla E-Ink Spectra 6 (800x480) del reTerminal E1002.

El driver epaper_spi de ESPHome NO tramea: cada píxel se fuerza a una de las 6 tintas con un umbral
duro (colorconv.h::color_to_bwyrgb). Por eso el tramado se hace aquí, contra las 6 tintas exactas,
y el firmware solo copia los códigos.

Modos:
  bn      Floyd-Steinberg a negro/blanco (fotos grises o de bajo color).
  bayer   Trama ordenada 8x8 a negro/blanco (look grabado, archivo más liviano).
  acento  bn + 6 tintas solo donde la foto es muy saturada (p. ej. ojos).
  color   Floyd-Steinberg a las 6 tintas.
  auto    bn si la foto es casi gris, color si no.
"""

import argparse
import math
import os
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter, ImageOps, ImageStat

CURRENT_DIR = Path(__file__).parent.resolve()
GALLERY_DIR = CURRENT_DIR / "gallery"
PREVIEWS_DIR = CURRENT_DIR / "previews"

# online_image decodifica el PNG en streaming (pngle_feed por trozos; solo el JPEG se carga completo), así que
# buffer_size (64 KB) no limita el archivo. Esto es solo una cota de cordura para el tiempo de descarga.
# shortcut: probado en el panel hasta 124 KB; si una imagen más grande no llega a pintarse, bajar el tope.
MAX_PNG_BYTES = 256 * 1024
SIZE = (800, 480)
# Orden de índices compartido por todas las salidas: negro, blanco, amarillo, rojo, verde, azul.
PANEL_CODES = [(0, 0, 0), (255, 255, 255), (255, 255, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255)]
# Tintas reales (apagadas) del panel: se tramea contra estas y se emiten los códigos puros.
# shortcut: valores aproximados de la literatura de Spectra 6, recalibrar con una foto del panel si el color se ve corrido.
PANEL_INKS = [(25, 30, 33), (232, 232, 232), (239, 222, 68), (178, 19, 24), (18, 95, 32), (33, 87, 186)]
GRAY_SATURATION = 40  # saturación HSV media bajo la cual una foto se trata como B/N
ACCENT_SATURATION = 110
ACCENT_MIN_VALUE = 80
BAYER8 = [
    [0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26],
    [12, 44, 4, 36, 14, 46, 6, 38], [60, 28, 52, 20, 62, 30, 54, 22],
    [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
    [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21],
]
MODES = ("auto", "bn", "bayer", "acento", "color")


def _palette_image(colors: list[tuple[int, int, int]]) -> Image.Image:
    p = Image.new("P", (1, 1))
    p.putpalette([v for c in colors for v in c])
    return p


def _indices(img: Image.Image) -> Image.Image:
    """Imagen P vista como imagen L de índices de paleta."""
    return Image.frombytes("L", img.size, img.tobytes())


def tone(img: Image.Image, strong: bool = True) -> Image.Image:
    """Levanta sombras según la propia foto y realza contraste local y detalle fino."""
    img = ImageOps.autocontrast(img, cutoff=1, preserve_tone=True)
    hist, half, acc = img.convert("L").histogram(), img.width * img.height // 2, 0
    median = next(i for i, n in enumerate(hist) if (acc := acc + n) >= half)
    gamma = min(1.0, max(0.4, math.log(0.45) / math.log(max(median, 1) / 255)))
    img = img.point([round(255 * (i / 255) ** gamma) for i in range(256)] * len(img.getbands()))
    if not strong:  # en color la trama de 6 tintas ya es ruidosa: realzar más la vuelve "frita"
        return img.filter(ImageFilter.UnsharpMask(radius=1, percent=60, threshold=3))
    img = img.filter(ImageFilter.UnsharpMask(radius=40, percent=50, threshold=0))  # pelaje y volúmenes
    return img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=2))  # bigotes y bordes


def dither_bn(img: Image.Image) -> Image.Image:
    return img.convert("L").convert("1").convert("L").point(lambda v: v >> 7)  # 0=negro, 1=blanco


def dither_bayer(img: Image.Image) -> Image.Image:
    lum = img.convert("L")
    src, out = lum.load(), Image.new("L", lum.size)
    dst = out.load()
    for y in range(lum.height):
        row = BAYER8[y & 7]
        for x in range(lum.width):
            dst[x, y] = 1 if src[x, y] > row[x & 7] * 4 + 2 else 0
    return out


def dither_color(img: Image.Image) -> Image.Image:
    return _indices(img.quantize(palette=_palette_image(PANEL_INKS), dither=Image.Dither.FLOYDSTEINBERG))


def dither_accent(img: Image.Image, original: Image.Image) -> Image.Image:
    # La máscara sale de la foto sin realzar: el unsharp crea halos saturados en los bordes.
    _, sat, val = original.convert("HSV").split()
    # En sombras la saturación HSV es ruido (20,15,10 => S~128): exigir también brillo.
    mask = ImageChops.darker(sat.point(lambda s: 255 if s > ACCENT_SATURATION else 0),
                             val.point(lambda v: 255 if v > ACCENT_MIN_VALUE else 0))
    mask = mask.filter(ImageFilter.MaxFilter(5))
    return Image.composite(dither_color(img), dither_bn(img), mask)


def resolve_mode(img: Image.Image, mode: str) -> str:
    if mode != "auto":
        return mode
    saturation = ImageStat.Stat(img.convert("HSV").getchannel("S")).mean[0]
    return "bn" if saturation < GRAY_SATURATION else "color"


def frame(im: Image.Image, crop_box: tuple[int, int, int, int] | None) -> Image.Image:
    if crop_box:
        cropped = im.crop(crop_box)
    else:
        w, h = im.size
        target_aspect = SIZE[0] / SIZE[1]
        if w / h > target_aspect:
            new_w = int(h * target_aspect)
            x_start = (w - new_w) // 2
            cropped = im.crop((x_start, 0, x_start + new_w, h))
        else:
            new_h = int(w / target_aspect)
            cropped = im.crop((0, 0, w, new_h))  # priorizar parte superior para cabezas/ojos
    return cropped.resize(SIZE, Image.Resampling.LANCZOS)


def render(indices: Image.Image, colors: list[tuple[int, int, int]]) -> Image.Image:
    """Índices -> PNG en modo P solo con las tintas usadas (2 => 1 bit/píxel, <=4 => 2 bits): pesa menos."""
    used = sorted(i for _, i in indices.getcolors(256))
    lut = [0] * 256
    for new, old in enumerate(used):
        lut[old] = new
    out = Image.frombytes("P", indices.size, indices.point(lut).tobytes())
    out.putpalette([v for i in used for v in colors[i]])
    return out


def adapt_photo(
    src_path: str | Path,
    dest_path: str | Path,
    preview_path: str | Path | None = None,
    crop_box: tuple[int, int, int, int] | None = None,
    mode: str = "auto",
) -> tuple[int, str]:
    """Devuelve (bytes del PNG, modo aplicado)."""
    if mode not in MODES:
        raise ValueError(f"Modo desconocido: {mode} (usa {', '.join(MODES)})")
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    im = frame(ImageOps.exif_transpose(Image.open(src_path)).convert("RGB"), crop_box)
    mode = resolve_mode(im, mode)
    toned = tone(im, strong=mode != "color")
    indices = dither_accent(toned, im) if mode == "acento" else \
        {"bn": dither_bn, "bayer": dither_bayer, "color": dither_color}[mode](toned)

    render(indices, PANEL_CODES).save(dest_path, format="PNG", optimize=True)
    if preview_path:
        preview_path = Path(preview_path)
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        render(indices, PANEL_INKS).save(preview_path, format="PNG", optimize=True)

    size = os.path.getsize(dest_path)
    if size > MAX_PNG_BYTES:
        raise ValueError(f"La imagen ({mode}) pesa demasiado: {size} > {MAX_PNG_BYTES} bytes")
    return size, mode


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Adapta una foto a la galería del reTerminal (Spectra 6, 800x480).")
    ap.add_argument("src")
    ap.add_argument("dest", help="p. ej. gallery/03_nombre.png")
    ap.add_argument("--mode", choices=MODES, default="auto")
    ap.add_argument("--preview", help="PNG con las tintas reales simuladas, para el dashboard")
    ap.add_argument("--crop", help="x0,y0,x1,y1 en píxeles del original (por defecto encuadre 5:3 automático)")
    args = ap.parse_args()
    crop = tuple(int(v) for v in args.crop.split(",")) if args.crop else None
    size, used_mode = adapt_photo(args.src, args.dest, preview_path=args.preview, crop_box=crop, mode=args.mode)
    print(f"Fotografía adaptada ({used_mode}): {size} bytes ({size / 1024:.1f} KB)")
