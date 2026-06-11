#!/usr/bin/env python3
"""Procedurally generate original 16x16 ore textures for the Glow Ores pack.

No Mojang/vanilla assets are read or copied — every pixel is generated here.

Usage:
    python generate_textures.py            # write textures + pack.png
    python generate_textures.py --preview  # also stitch tools/preview.png
"""

import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 16
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "pack" / "assets" / "minecraft" / "textures" / "block"
PACK_ICON = Path(__file__).resolve().parent.parent / "pack" / "pack.png"
PREVIEW_PATH = Path(__file__).resolve().parent / "preview.png"

# Speckle color (R, G, B) and glow/outline color per ore.
# Tweak these to adjust how each ore reads in-game.
ORE_COLORS = {
    "coal_ore":          {"speckle": (38, 38, 42),    "glow": (200, 200, 210)},
    "iron_ore":          {"speckle": (216, 175, 147), "glow": (255, 230, 200)},
    "copper_ore":        {"speckle": (224, 122, 80),  "glow": (255, 190, 130)},
    "gold_ore":          {"speckle": (250, 210, 60),  "glow": (255, 255, 160)},
    "redstone_ore":      {"speckle": (220, 30, 30),   "glow": (255, 110, 110)},
    "lapis_ore":         {"speckle": (40, 80, 200),   "glow": (130, 180, 255)},
    "diamond_ore":       {"speckle": (90, 230, 220),  "glow": (190, 255, 250)},
    "emerald_ore":       {"speckle": (40, 200, 90),   "glow": (150, 255, 180)},
    "nether_gold_ore":   {"speckle": (250, 210, 60),  "glow": (255, 255, 160)},
    "nether_quartz_ore": {"speckle": (235, 230, 222), "glow": (255, 255, 255)},
}

OVERWORLD_ORES = [
    "coal_ore", "iron_ore", "copper_ore", "gold_ore",
    "redstone_ore", "lapis_ore", "diamond_ore", "emerald_ore",
]
NETHER_ORES = ["nether_gold_ore", "nether_quartz_ore"]

# Background base tones (R, G, B) with per-pixel noise applied on top.
STONE_BASE = (126, 126, 126)
DEEPSLATE_BASE = (70, 70, 74)
NETHERRACK_BASE = (97, 54, 52)


def make_background(rng, base, noise=10):
    """Neutral stone-like noise background with subtle per-pixel variation."""
    img = Image.new("RGB", (SIZE, SIZE))
    px = img.load()
    for y in range(SIZE):
        for x in range(SIZE):
            n = rng.randint(-noise, noise)
            px[x, y] = tuple(max(0, min(255, c + n)) for c in base)
    return img


def make_chunk(rng, cx, cy, size):
    """Grow a compact irregular nugget of ~`size` connected pixels around (cx, cy).

    Growth is clamped to a 5x5 box around the seed so nuggets stay chunky, and
    to [2, 13] so the 1px outline never reaches the tile edge (clean tiling).
    """
    chunk = {(cx, cy)}
    for _ in range(size * 8):
        if len(chunk) >= size:
            break
        x, y = rng.choice(sorted(chunk))
        dx, dy = rng.choice([(-1, 0), (1, 0), (0, -1), (0, 1)])
        nx, ny = x + dx, y + dy
        if 2 <= nx <= 13 and 2 <= ny <= 13 and abs(nx - cx) <= 2 and abs(ny - cy) <= 2:
            chunk.add((nx, ny))
    return chunk


def ore_chunks(rng):
    """Scatter 3-5 separate ore nuggets of varied size across the tile.

    Chunks keep a >=3px Chebyshev gap from each other so every nugget gets its
    own distinct outline ring.
    """
    chunks = []
    occupied = set()
    target = rng.randint(3, 5)
    for _ in range(200):
        if len(chunks) >= target:
            break
        cx, cy = rng.randint(3, 12), rng.randint(3, 12)
        chunk = make_chunk(rng, cx, cy, size=rng.randint(3, 8))
        if any(abs(x - ox) <= 2 and abs(y - oy) <= 2
               for x, y in chunk for ox, oy in occupied):
            continue
        chunks.append(chunk)
        occupied |= chunk
    return chunks


def outline_of(mask):
    """1px ring of pixels orthogonally adjacent to the speckles."""
    ring = set()
    for x, y in mask:
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < SIZE and 0 <= ny < SIZE and (nx, ny) not in mask:
                ring.add((nx, ny))
    return ring


def shade(color, rng, spread=18):
    """Slightly vary a color so speckle blobs aren't flat."""
    n = rng.randint(-spread, spread)
    return tuple(max(0, min(255, c + n)) for c in color)


def tint(color, amount):
    """Uniformly brighten (+) or darken (-) a color."""
    return tuple(max(0, min(255, c + amount)) for c in color)


def generate_texture(name, base, seed):
    """Return (base_img, glow_img).

    base_img: full RGB ore tile (background + speckles + outline).
    glow_img: RGBA emissive layer — only the speckles and outline are opaque,
    everything else is alpha 0 so the stone background stays normally lit.
    """
    rng = random.Random(seed)
    colors = ORE_COLORS[name.removeprefix("deepslate_")]
    img = make_background(rng, base)
    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    px, gpx = img.load(), glow.load()

    chunks = ore_chunks(rng)
    mask = set().union(*chunks)
    # Bright high-contrast outline first, ore chunks drawn over the top.
    for x, y in outline_of(mask):
        px[x, y] = colors["glow"]
        gpx[x, y] = colors["glow"] + (255,)
    # 2-tone shading per chunk: one bright core pixel, slightly darker body.
    for chunk in chunks:
        n = len(chunk)
        cx = sum(x for x, _ in chunk) / n
        cy = sum(y for _, y in chunk) / n
        core = min(sorted(chunk), key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
        for x, y in sorted(chunk):
            if (x, y) == core:
                c = tint(colors["speckle"], 45)
            else:
                c = shade(tint(colors["speckle"], -22), rng, spread=10)
            px[x, y] = c
            gpx[x, y] = c + (255,)
    return img, glow


def generate_all():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    created = []
    jobs = []
    for ore in OVERWORLD_ORES:
        jobs.append((ore, STONE_BASE))
        jobs.append((f"deepslate_{ore}", DEEPSLATE_BASE))
    for ore in NETHER_ORES:
        jobs.append((ore, NETHERRACK_BASE))

    for name, base in jobs:
        base_img, glow_img = generate_texture(name, base, seed=name)
        base_path = OUTPUT_DIR / f"{name}.png"
        glow_path = OUTPUT_DIR / f"{name}_glow.png"
        base_img.save(base_path)
        glow_img.save(glow_path)
        created.extend([base_path, glow_path])
    return created


def generate_pack_icon():
    """128x128 icon: dark stone field with glowing ore speckles."""
    rng = random.Random("glow-ores-icon")
    img = Image.new("RGB", (128, 128))
    px = img.load()
    for y in range(128):
        for x in range(128):
            n = rng.randint(-8, 8)
            px[x, y] = tuple(max(0, min(255, c + n)) for c in (58, 58, 64))

    draw = ImageDraw.Draw(img)
    glow_ores = ["diamond_ore", "gold_ore", "redstone_ore", "emerald_ore", "lapis_ore", "copper_ore"]
    spots = [(28, 30), (84, 24), (50, 64), (96, 80), (24, 92), (66, 102)]
    for ore, (cx, cy) in zip(glow_ores, spots):
        c = ORE_COLORS[ore]
        draw.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], outline=c["glow"], width=3)
        draw.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=c["speckle"])

    img.save(PACK_ICON)
    return PACK_ICON


def generate_preview(texture_paths, scale=16, cols=6):
    """Stitch all textures into one labeled grid, each tile scaled up."""
    tile = SIZE * scale
    label_h = 24
    pad = 8
    rows = (len(texture_paths) + cols - 1) // cols
    sheet = Image.new(
        "RGB",
        (cols * (tile + pad) + pad, rows * (tile + label_h + pad) + pad),
        (24, 24, 28),
    )
    draw = ImageDraw.Draw(sheet)

    for i, path in enumerate(sorted(texture_paths)):
        r, c = divmod(i, cols)
        x = pad + c * (tile + pad)
        y = pad + r * (tile + label_h + pad)
        img = Image.open(path).convert("RGBA")
        backing = Image.new("RGBA", img.size, (10, 10, 12, 255))
        img = Image.alpha_composite(backing, img).convert("RGB")
        sheet.paste(img.resize((tile, tile), Image.NEAREST), (x, y))
        draw.text((x + 2, y + tile + 4), path.stem, fill=(230, 230, 230))

    sheet.save(PREVIEW_PATH)
    return PREVIEW_PATH


def main():
    parser = argparse.ArgumentParser(description="Generate Glow Ores textures")
    parser.add_argument("--preview", action="store_true",
                        help="also stitch all textures into tools/preview.png")
    args = parser.parse_args()

    created = generate_all()
    icon = generate_pack_icon()
    print(f"Wrote {len(created)} textures to {OUTPUT_DIR}")
    for p in created:
        print(f"  {p.name}")
    print(f"Wrote pack icon: {icon}")

    if args.preview:
        preview = generate_preview(created)
        print(f"Wrote preview sheet: {preview}")


if __name__ == "__main__":
    main()
