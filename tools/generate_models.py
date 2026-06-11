#!/usr/bin/env python3
"""Generate vanilla block model + blockstate JSONs for the emissive ores.

Targets Minecraft Java 26.1.2 (pack format 84) native emissive support:
- Each model has two full-cube elements. The first uses the base ore texture
  and is lit normally. The second uses the <ore>_glow overlay texture and sets
  "light_emission": 15 (added in 1.21.2) so it renders fullbright, plus
  "shade": false so directional face shading doesn't dim the glow.
- The glow texture's background is fully transparent; since 26.1 any block
  model sprite with fully transparent pixels is automatically rendered in the
  cutout pass (drawn after solid), so only the ore pixels glow and the stone
  background underneath stays normally lit.

Models overwrite the vanilla paths (assets/minecraft/models/block/<ore>.json),
so item forms pick them up automatically. Blockstates are also written so the
redstone ores' lit=true/lit=false states both use our model.

Usage:
    python generate_models.py
"""

import json
from pathlib import Path

from generate_textures import NETHER_ORES, OVERWORLD_ORES

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "pack" / "assets" / "minecraft"
MODELS_DIR = ASSETS / "models" / "block"
BLOCKSTATES_DIR = ASSETS / "blockstates"

DIRECTIONS = ["down", "up", "north", "south", "west", "east"]

# Blocks whose vanilla blockstate has a lit=true/false property.
LIT_ORES = {"redstone_ore", "deepslate_redstone_ore"}


def all_ores():
    names = []
    for ore in OVERWORLD_ORES:
        names.append(ore)
        names.append(f"deepslate_{ore}")
    names.extend(NETHER_ORES)
    return names


def cube(texture_var, emissive=False):
    element = {
        "from": [0, 0, 0],
        "to": [16, 16, 16],
        "faces": {d: {"texture": texture_var, "cullface": d} for d in DIRECTIONS},
    }
    if emissive:
        element["shade"] = False
        element["light_emission"] = 15
    return element


def model_json(name):
    return {
        "parent": "minecraft:block/block",
        "textures": {
            "particle": f"minecraft:block/{name}",
            "base": f"minecraft:block/{name}",
            "glow": f"minecraft:block/{name}_glow",
        },
        "elements": [cube("#base"), cube("#glow", emissive=True)],
    }


def blockstate_json(name):
    variant = {"model": f"minecraft:block/{name}"}
    if name in LIT_ORES:
        return {"variants": {"lit=false": variant, "lit=true": variant}}
    return {"variants": {"": variant}}


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    BLOCKSTATES_DIR.mkdir(parents=True, exist_ok=True)

    for name in all_ores():
        model_path = MODELS_DIR / f"{name}.json"
        state_path = BLOCKSTATES_DIR / f"{name}.json"
        model_path.write_text(json.dumps(model_json(name), indent=2) + "\n")
        state_path.write_text(json.dumps(blockstate_json(name), indent=2) + "\n")
        print(f"  {model_path.relative_to(ROOT)}")
        print(f"  {state_path.relative_to(ROOT)}")

    print(f"Wrote {len(all_ores())} models and {len(all_ores())} blockstates")


if __name__ == "__main__":
    main()
