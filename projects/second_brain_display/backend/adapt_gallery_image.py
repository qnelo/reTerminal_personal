#!/usr/bin/env python3
"""
adapt_gallery_image.py
Adapta una fotografía o imagen arbitraria para la pantalla E-Ink Spectra 6 (800x480)
del Seeed Studio reTerminal E1002:
- Encuadre inteligente con relación de aspecto 5:3 (800x480).
- Realce de contraste y micro-detalles (bigotes, pelaje, ojos).
- Cuantización a 11-16 colores con tramado Floyd-Steinberg.
- Garantía estricta de tamaño de archivo < 64 KB (65.536 bytes) para el buffer de ESPHome.
"""

import sys
import os
from pathlib import Path
from PIL import Image, ImageEnhance

CURRENT_DIR = Path(__file__).parent.resolve()
GALLERY_DIR = CURRENT_DIR / "gallery"
PREVIEWS_DIR = CURRENT_DIR / "previews"


def adapt_photo(
    src_path: str | Path,
    dest_path: str | Path,
    preview_path: str | Path | None = None,
    crop_box: tuple[int, int, int, int] | None = None,
    colors: int = 11,
    boost_eyes: bool = True,
) -> int:
    src_path = Path(src_path)
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    im = Image.open(src_path)
    w, h = im.size

    if crop_box:
        cropped = im.crop(crop_box)
    else:
        # Encuadre automático 5:3 manteniendo el ancho o alto proporcional
        target_aspect = 800.0 / 480.0
        current_aspect = float(w) / float(h)
        if current_aspect > target_aspect:
            # Demasiado ancha: recortar lados
            new_w = int(h * target_aspect)
            x_start = (w - new_w) // 2
            cropped = im.crop((x_start, 0, x_start + new_w, h))
        else:
            # Demasiado alta: recortar arriba/abajo
            new_h = int(w / target_aspect)
            y_start = 0  # Priorizar parte superior para cabezas/ojos
            cropped = im.crop((0, y_start, w, y_start + new_h))

    resized = cropped.resize((800, 480), Image.Resampling.LANCZOS)

    if boost_eyes:
        rw, rh = resized.size
        for x in range(rw):
            for y in range(rh):
                r, g, b = resized.getpixel((x, y))
                if 240 <= x <= 460 and 150 <= y <= 230:
                    if g > 90 and g > b + 15:
                        new_r = min(255, int(r * 0.95))
                        new_g = min(255, int(g * 1.3))
                        new_b = max(0, int(b * 0.55))
                        resized.putpixel((x, y), (new_r, new_g, new_b))

    enhanced = ImageEnhance.Brightness(resized).enhance(1.05)
    enhanced = ImageEnhance.Contrast(enhanced).enhance(1.15)

    quant = enhanced.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
    quant.save(dest_path, format="PNG", optimize=True)

    if preview_path:
        preview_path = Path(preview_path)
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        quant.save(preview_path, format="PNG", optimize=True)

    size = os.path.getsize(dest_path)
    if size > 65536:
        raise ValueError(f"La imagen excede el límite de 64 KB de ESPHome: {size} bytes")

    return size


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "/tmp/cat_full.jpg"
    dest = sys.argv[2] if len(sys.argv) > 2 else GALLERY_DIR / "02_gatito.png"
    prev = PREVIEWS_DIR / "gatito.png"
    size = adapt_photo(src, dest, preview_path=prev, crop_box=(0, 0, 4096, 2458))
    print(f"Fotografía adaptada exitosamente: {size} bytes ({size/1024:.1f} KB)")
