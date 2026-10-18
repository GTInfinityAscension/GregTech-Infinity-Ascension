#!/usr/bin/env python3
"""Isometric pixel images of multiblocks for the quest book, drawn from the real block textures.

    iso_render.py <machine id> <out.png> [--block 8] [--max 128]

Shapes come from tools/data/multiblock_shapes.json (written by the GTIACore GameTest ShapeDumpGameTests); textures
from the mod jars in the mod cache and from the GTIACore resources. Machines and hatches have dynamic models, so a
controller is drawn as its casing with its front overlay and a hatch as a voltage hull side.
"""
import argparse
import collections
import io
import json
import os
import sys
import zipfile
from pathlib import Path

from PIL import Image, ImageEnhance

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / "MineProjects/GTIA-arquivo/mod-cache"
CORE_ASSETS = Path.home() / "MineProjects/GTIA/core/src/main/resources/assets"
CORE_GEN = Path.home() / "MineProjects/GTIA/core/src/generated/resources/assets"
SHAPES = ROOT / "tools/data/multiblock_shapes.json"
# Casing a controller of another mod shows; GTIA controllers take the most common casing of their structure.
CONTROLLER_CASING = {"gtceu:large_chemical_reactor": "gtceu:inert_machine_casing",
                     "gtceu:electric_blast_furnace": "gtceu:heatproof_machine_casing",
                     "gtceu:vacuum_freezer": "gtceu:frostproof_machine_casing",
                     "gtceu:distillation_tower": "gtceu:clean_machine_casing",
                     "gtceu:cracker": "gtceu:clean_machine_casing",
                     "gtceu:steel_large_boiler": "gtceu:solid_machine_casing"}


class Assets:
    def __init__(self):
        self.zips = {}
        extra = [Path(p) for p in os.environ.get("GTIA_EXTRA_JARS", "").split(os.pathsep) if p]
        for jar in sorted(CACHE.glob("*.jar")) + extra:
            try:
                z = zipfile.ZipFile(jar)
            except zipfile.BadZipFile:
                continue
            for ns in {n.split("/")[1] for n in z.namelist() if n.startswith("assets/") and n.count("/") > 1}:
                self.zips.setdefault(ns, []).append(z)
        # A mod's own jar wins over add-ons that ship textures in its namespace.
        for ns, jars in self.zips.items():
            jars.sort(key=lambda z: not Path(z.filename).name.startswith(ns))

    def read(self, path: str) -> bytes | None:
        for base in (CORE_ASSETS, CORE_GEN):
            f = base / path
            if f.is_file():
                return f.read_bytes()
        ns = path.split("/")[0]
        for z in self.zips.get(ns, []):
            try:
                return z.read("assets/" + path)
            except KeyError:
                continue
        return None

    def texture(self, ref: str) -> Image.Image | None:
        ns, path = ref.split(":", 1) if ":" in ref else ("minecraft", ref)
        data = self.read(f"{ns}/textures/{path}.png")
        if data is None:
            return None
        im = Image.open(io.BytesIO(data)).convert("RGBA")
        return im.crop((0, 0, im.width, im.width))  # first frame of an animation

    def model_textures(self, ref: str, depth=0) -> dict:
        ns, path = ref.split(":", 1) if ":" in ref else ("minecraft", ref)
        data = self.read(f"{ns}/models/{path}.json")
        if data is None or depth > 8:
            return {}
        model = json.loads(data)
        textures = {}
        if "parent" in model:
            textures.update(self.model_textures(model["parent"], depth + 1))
        textures.update(model.get("textures", {}))
        return textures

    def block_faces(self, block: str):
        ns, name = block.split(":", 1)
        data = self.read(f"{ns}/blockstates/{name}.json")
        if data is None:
            return None
        state = json.loads(data)
        variant = next(iter(state.get("variants", {}).values()), None)
        if variant is None and "multipart" in state:
            variant = state["multipart"][0]["apply"]
        if isinstance(variant, list):
            variant = variant[0]
        if not variant:
            return None
        tex = self.model_textures(variant["model"])

        def resolve(key):
            seen = 0
            value = tex.get(key)
            while isinstance(value, str) and value.startswith("#") and seen < 8:
                value, seen = tex.get(value[1:]), seen + 1
            return value
        side = next((resolve(k) for k in ("side", "all", "north", "texture", "end", "particle") if resolve(k)), None)
        top = next((resolve(k) for k in ("top", "end", "up", "all", "side", "particle") if resolve(k)), side)
        if side is None:
            return None
        return self.texture(top), self.texture(side)


def face(texture, size, kind):
    """Maps a texture onto the top rhombus or a side parallelogram, nearest neighbour, at block size `size`."""
    s = size
    t = texture.resize((16, 16), Image.NEAREST)
    if kind == "top":
        out = Image.new("RGBA", (2 * s, s), (0, 0, 0, 0))
        for y in range(s):
            for x in range(2 * s):
                # screen -> texture: u along (+x,+y/2), v along (-x,+y/2)
                dx, dy = x - s + 0.5, y + 0.5
                u = (dx / s + 2 * dy / s) / 2
                v = (-dx / s + 2 * dy / s) / 2
                if 0 <= u < 1 and 0 <= v < 1:
                    out.putpixel((x, y), t.getpixel((int(u * 16), int(v * 16))))
        return out
    out = Image.new("RGBA", (s, s + s // 2), (0, 0, 0, 0))
    for y in range(s + s // 2):
        for x in range(s):
            u = (x + 0.5) / s
            slope = u / 2 if kind == "left" else (1 - u) / 2
            v = ((y + 0.5) / s) - slope
            if 0 <= v < 1:
                px = t.getpixel((int(u * 16) if kind == "left" else int(u * 16), int(v * 16)))
                out.putpixel((x, y), px)
    shade = 0.82 if kind == "left" else 0.64
    rgb, a = out.convert("RGB"), out.getchannel("A")
    rgb = ImageEnhance.Brightness(rgb).enhance(shade)
    rgb.putalpha(a)
    return rgb


def render(machine: str, block_px: int, max_px: int | None, blocks: list | None = None) -> Image.Image:
    """Renders a machine from the shape dump, or any block list [[x, y, z, block, facing], ...] given as `blocks`."""
    if blocks is None:
        blocks = json.loads(SHAPES.read_text())[machine]
    assets = Assets()
    counts = collections.Counter(b[3] for b in blocks if "casing" in b[3] or "firebox" in b[3])
    majority = counts.most_common(1)[0][0] if counts else "gtceu:solid_machine_casing"
    controller_casing = CONTROLLER_CASING.get(machine, majority)
    cache = {}

    def faces_of(block, facing):
        key = (block, facing)
        if key in cache:
            return cache[key]
        result = None
        if block == machine:
            top, side = assets.block_faces(controller_casing)
            ns, name = machine.split(":")
            overlay = assets.texture(f"{ns}:block/multiblock/{name}/overlay_front") or \
                assets.texture(f"{ns}:block/machines/{name}/overlay_front")
            front = side.copy()
            if overlay:
                front.alpha_composite(overlay.resize(front.size, Image.NEAREST))
            result = (top, side, front)
        elif "hatch" in block or "_bus" in block:
            # The preview fills every hatch slot; a built machine shows mostly casing.
            f = assets.block_faces(majority)
            result = (f[0], f[1], f[1])
        else:
            f = assets.block_faces(block)
            if f:
                result = (f[0], f[1], f[1])
        cache[key] = result
        return result

    s = block_px
    xs = [b[0] for b in blocks]; ys = [b[1] for b in blocks]; zs = [b[2] for b in blocks]
    w = (max(xs) - min(xs) + max(zs) - min(zs) + 2) * s
    h = (max(xs) - min(xs) + max(zs) - min(zs) + 2) * s // 2 + (max(ys) - min(ys) + 1) * s + s
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ox = (max(zs) - min(zs) + 1) * s
    oy = (max(ys) - min(ys) + 1) * s
    # Frames, glass and bars do not hide the faces behind them.
    see_through = ("frame", "glass", "bars")
    occupied = {(b[0], b[1], b[2]) for b in blocks if not any(t in b[3] for t in see_through)}
    face_cache = {}
    # Painter's order: far to near (small x+z first), bottom to top.
    for x, y, z, block, facing in sorted(blocks, key=lambda b: (b[0] + b[2], b[1])):
        tex = faces_of(block, facing)
        if tex is None:
            continue
        top, side, front = tex
        sx = ox + (x - min(xs)) * s - (z - min(zs)) * s
        sy = oy + ((x - min(xs)) + (z - min(zs))) * s // 2 - (y - min(ys)) * s
        # The camera looks from +x+z; the visible sides are +z (left) and +x (right).
        left_tex = front if facing == "south" else side
        right_tex = front if facing == "east" else side
        for kind, t, dx, dy, hidden in (("top", top, -s, -s, (x, y + 1, z) in occupied),
                                        ("left", left_tex, -s, -s // 2, (x, y, z + 1) in occupied),
                                        ("right", right_tex, 0, -s // 2, (x + 1, y, z) in occupied)):
            if hidden or t is None:
                continue
            k = (id(t), kind)
            if k not in face_cache:
                face_cache[k] = face(t, s, kind)
            f = face_cache[k]
            img.alpha_composite(f, (sx + dx + s, sy + dy + s // 2))
    img = img.crop(img.getbbox())
    if max_px and max(img.size) > max_px:
        k = max_px / max(img.size)
        img = img.resize((max(1, int(img.width * k)), max(1, int(img.height * k))), Image.NEAREST)
    return img


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("machine")
    ap.add_argument("out")
    ap.add_argument("--block", type=int, default=8)
    ap.add_argument("--max", type=int, default=None)
    a = ap.parse_args()
    render(a.machine, a.block, a.max).save(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
