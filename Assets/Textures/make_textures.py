#!/usr/bin/env python3
"""
Seamless tileable texture generator for Blender / UE5.

Usage:
    python make_textures.py                # generates everything into ./textures
    python make_textures.py --size 4096 --squares 16 --out my_textures

All textures tile perfectly because pattern frequencies are whole numbers
that divide the image size (or, for noise, are generated via FFT, which is
inherently periodic).

Requires: numpy, pillow
"""
import argparse
import os
import numpy as np
from PIL import Image


def save(arr, path, mode=None):
    Image.fromarray(arr, mode).save(path)
    print("wrote", path)


def checker(size, squares, c0=0, c1=255):
    """squares must be EVEN so the pattern wraps cleanly."""
    assert squares % 2 == 0, "squares must be even for seamless tiling"
    assert size % squares == 0, "size must be divisible by squares"
    cell = size // squares
    y, x = np.indices((size, size))
    mask = ((x // cell) + (y // cell)) % 2
    return np.where(mask == 0, c1, c0).astype(np.uint8)


def stripes(size, count, vertical=True):
    assert size % count == 0
    band = size // count
    idx = np.indices((size, size))[1 if vertical else 0] // band
    return np.where(idx % 2 == 0, 255, 0).astype(np.uint8)


def dots(size, count, radius=0.3):
    cell = size / count
    y, x = np.indices((size, size))
    fx = (x % cell) / cell - 0.5
    fy = (y % cell) / cell - 0.5
    return np.where(np.hypot(fx, fy) < radius, 255, 0).astype(np.uint8)


def grid_lines(size, count, thickness_px):
    cell = size // count
    y, x = np.indices((size, size))
    line = ((x % cell) < thickness_px) | ((y % cell) < thickness_px)
    return np.where(line, 0, 255).astype(np.uint8)


def noise(size, power=2.0, seed=0):
    """Periodic 'cloud' noise via FFT -- tiles seamlessly by construction."""
    rng = np.random.default_rng(seed)
    white = rng.standard_normal((size, size))
    fx = np.fft.fftfreq(size)[:, None]
    fy = np.fft.fftfreq(size)[None, :]
    f = np.sqrt(fx**2 + fy**2)
    f[0, 0] = 1.0
    spectrum = np.fft.fft2(white) / (f ** (power / 2))
    spectrum[0, 0] = 0
    out = np.real(np.fft.ifft2(spectrum))
    out = (out - out.min()) / (out.max() - out.min())
    return (out * 255).astype(np.uint8)


def height_to_normal(height_u8, strength=4.0):
    """Tileable tangent-space normal map (OpenGL / Y+ convention, wraps at edges)."""
    h = height_u8.astype(np.float32) / 255.0
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5
    nx, ny, nz = -dx * strength, dy * strength, np.ones_like(h)  # +Y up (Blender/OpenGL)
    length = np.sqrt(nx**2 + ny**2 + nz**2)
    n = np.stack([nx / length, ny / length, nz / length], axis=-1)
    return ((n * 0.5 + 0.5) * 255).astype(np.uint8)


def tile_preview(arr, n=3, preview_size=1536):
    """Tiles the texture n x n so you can eyeball seams."""
    im = Image.fromarray(arr)
    big = Image.new(im.mode, (im.width * n, im.height * n))
    for i in range(n):
        for j in range(n):
            big.paste(im, (i * im.width, j * im.height))
    return big.resize((preview_size, preview_size), Image.LANCZOS)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--size", type=int, default=2048, help="texture resolution (px)")
    p.add_argument("--squares", type=int, default=8, help="checker squares per side (even)")
    p.add_argument("--out", default="textures")
    a = p.parse_args()

    os.makedirs(a.out, exist_ok=True)
    S = a.size

    # Core request: black & white checkerboard
    chk = checker(S, a.squares)
    save(chk, f"{a.out}/checker_bw_{S}.png", "L")
    # Normal map companion (flat -> pure +Z; handy for material slots needing one)
    save(height_to_normal(chk, strength=0.0), f"{a.out}/flat_normal_{S}.png")

    # Extras
    save(checker(S, a.squares, c0=40, c1=215), f"{a.out}/checker_soft_{S}.png", "L")
    save(stripes(S, a.squares * 2), f"{a.out}/stripes_{S}.png", "L")
    save(dots(S, a.squares), f"{a.out}/dots_{S}.png", "L")
    save(grid_lines(S, a.squares, max(2, S // 256)), f"{a.out}/grid_{S}.png", "L")

    n = noise(S, power=2.2, seed=7)
    save(n, f"{a.out}/clouds_{S}.png", "L")
    save(height_to_normal(n, strength=6.0), f"{a.out}/clouds_normal_{S}.png")

    # Seam-check preview
    tile_preview(chk).save(f"{a.out}/_preview_checker_3x3.png")
    tile_preview(n).save(f"{a.out}/_preview_clouds_3x3.png")
    print("done")


if __name__ == "__main__":
    main()
