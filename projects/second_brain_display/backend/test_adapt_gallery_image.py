#!/usr/bin/env python3
"""Self-check de la galería (fotos adaptadas y árbol Buendía): la salida ya está en las 6 tintas puras, así que el
firmware no re-mapea nada.

Uso: .venv/bin/python projects/second_brain_display/backend/test_adapt_gallery_image.py
"""

import colorsys
import tempfile
from pathlib import Path
from PIL import Image

from adapt_gallery_image import MAX_PNG_BYTES, MODES, PANEL_CODES, adapt_photo
from generate_cien_anos_tree import generate_tree_image


def firmware_color(r: int, g: int, b: int) -> tuple[int, int, int]:
    """Réplica de colorconv.h::color_to_bwyrgb (ESPHome epaper_spi), devuelta como código puro."""
    K, W, Y, R, G, B = PANEL_CODES
    if max(r, g, b) - min(r, g, b) < 50:
        return W if (77 * r + 150 * g + 29 * b + 128) >> 8 >= 128 else K
    ro, go, bo = r > 128, g > 128, b > 128
    if ro and go and not bo:
        return Y
    if ro and not go and not bo:
        return R
    if not ro and go and not bo:
        return G
    if not ro and not go and bo:
        return B
    if not ro and go and bo:
        return G
    if ro and not go:
        return R
    return W if ro else K


def gray_ramp() -> Image.Image:
    return Image.linear_gradient("L").resize((1000, 600)).convert("RGB")


def rainbow() -> Image.Image:
    im = Image.new("RGB", (360, 200))
    for x in range(360):
        for y in range(200):
            im.putpixel((x, y), tuple(round(v * 255) for v in colorsys.hsv_to_rgb(x / 360, 1, 0.3 + y / 285)))
    return im.resize((1000, 600))


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name, img in (("gris", gray_ramp()), ("arcoiris", rainbow())):
            src = tmp / f"{name}.png"
            img.save(src)
            for mode in MODES:
                dest = tmp / f"{name}_{mode}.png"
                try:
                    size, used = adapt_photo(src, dest, mode=mode)
                except ValueError as e:  # la trama a color puede pasarse del buffer; B/N nunca
                    assert mode not in ("bn", "bayer"), e
                    size, used = dest.stat().st_size, e.args[0].split("(")[1].split(")")[0]
                out = Image.open(dest)
                assert out.mode == "P" and out.size == (800, 480), (name, mode, out.mode, out.size)
                colors = {c for _, c in out.convert("RGB").getcolors(16)}
                assert colors <= set(PANEL_CODES), (name, mode, colors)
                assert all(firmware_color(*c) == c for c in colors), (name, mode)
                if mode in ("bn", "bayer"):
                    assert colors <= set(PANEL_CODES[:2]) and size <= MAX_PNG_BYTES, (name, mode, size)
                if mode == "auto":
                    assert used == ("bn" if name == "gris" else "color"), (name, used)
                print(f"ok {name:9s} {mode:7s} -> {used:6s} {size:6d} B  {len(colors)} tintas")

        tree = tmp / "arbol.png"
        generate_tree_image(tree)
        out = Image.open(tree)
        colors = {c for _, c in out.convert("RGB").getcolors(16)}
        assert out.mode == "P" and out.size == (800, 480) and colors <= set(PANEL_CODES), colors
        assert all(firmware_color(*c) == c for c in colors) and tree.stat().st_size <= MAX_PNG_BYTES
        print(f"ok árbol Buendía {tree.stat().st_size:6d} B  {len(colors)} tintas")


if __name__ == "__main__":
    main()
