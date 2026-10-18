#!/usr/bin/env python3
"""Writes quests-src/multiblocks.toml, the data of the Multiblock Goals chapter (D-291, after GTNH's).

    multiblock_goals.py

For every multiblock of the pack export (manifest/registry/pack/machines.jsonl):
- tier: the voltage its cheapest controller recipe needs, counting the tier of every part (hulls, circuits,
  components), the way GTNH sorts its Multiblock Goals; parts without a tier in their name are followed through
  their own recipes;
- family: the column it goes in, from its id (FAMILIES below; the first match wins);
- text: the lang keys its own mod has for it (multiblock description, tooltip lines), so the quest shows the mod's
  text in every language.
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reach  # noqa: E402

PACK = Path(__file__).resolve().parents[1]
OUT = PACK / "quests-src" / "multiblocks.toml"
CACHE = Path.home() / "MineProjects" / "GTIA-arquivo" / "mod-cache"
FAMILIES = [
    ("steam", r"steam|primitive|coke|brick|bronze_large|cactus|cobbler|woodcutter"),
    ("power", r"turbine|generator|boiler|combustion|fuel_cell|fusion|dynamo|solar|plasma|nuclear|lightning|"
              r"transformer|reactor_core"),
    ("ore", r"ore|miner|mill|washer|sifter|sifting|crush|macerat|drill|quarry|void|mining|flotation|"
            r"resource_collection"),
    ("chemistry", r"chemical|distill|crack|electroly|centrifug|mixer|vat|claus|kroll|siemens|ostwald|bayer|hall_|"
                  r"contact|ammonia|solvay|diaphragm|retort|lime|brew|ferment|purif|refiner|dehydr|polymer|"
                  r"desulfur|evaporat|autoclave|vapor_deposition"),
    ("metal", r"blast|furnace|freezer|smelt|foundry|alloy|forge|arc|cool|heat|kiln|oven|casting|crucible|sinter"),
    ("processing", r"assembl|circuit|component|laser|engrav|cutter|cutting|lathe|bender|press|extrud|extract|"
                   r"wiremill|pcb|packer|canner|manufact|fabricat|solidif|electromagnet|rolling|factory"),
    ("bio", r"greenhouse|apiary|bee|farm|tree|crop|bio|algae|incubat|slaughter|fishing|eye_of_wood"),
    ("space", r"space|rocket|elevator|station|planet|dimension|orbit|satellite|lunar|moon|dyson"),
    ("data", r"tank|storage|drum|chest|quantum|_me_|data|computer|computation|research|network|monitor|uplink|"
             r"nexus|vault"),
]
LANG_PATTERNS = ["{ns}.multiblock.{path}.description", "{ns}.machine.{path}.tooltip", "{ns}.machine.{path}.tooltip.{n}"]


def lang_tables() -> dict[str, dict[str, str]]:
    """en_us of the mods that own multiblocks, from the newest jar of each in the mod cache."""
    tables = {}
    lock = json.loads((PACK / "manifest" / "full.lock.json").read_text())
    jars = {m["mod_id"]: CACHE / m["filename"] for m in lock["mods"]}
    for ns, mod in (("gtceu", "gtceu"), ("gtna", "gtna"), ("gtia", "gtia"), ("modern_manipulator", "modern_manipulator")):
        jar = jars.get(mod)
        if not jar or not jar.exists():
            continue
        with zipfile.ZipFile(jar) as z:
            name = f"assets/{ns}/lang/en_us.json"
            if name in z.namelist():
                tables[ns] = json.loads(z.read(name))
    gtia = PACK.parent / "core" / "src" / "generated" / "resources" / "assets" / "gtia" / "lang" / "en_us.json"
    if gtia.exists():
        tables["gtia"] = json.loads(gtia.read_text())
    return tables


def text_keys(item: str, tables: dict[str, dict[str, str]]) -> list[str]:
    ns, path = item.split(":", 1)
    table = tables.get(ns, {})
    keys = []
    for pattern in LANG_PATTERNS:
        if "{n}" in pattern:
            n = 0
            while pattern.format(ns=ns, path=path, n=n) in table:
                keys.append(pattern.format(ns=ns, path=path, n=n))
                n += 1
        elif pattern.format(ns=ns, path=path) in table:
            keys.append(pattern.format(ns=ns, path=path))
    # GTIA tooltips are sectioned (fact, main, auxiliary, requirements)
    keys += sorted(k for k in table if k.startswith(f"gtia.machine.{path}.tooltip.") and k not in keys
                   and ns == "gtia")
    return keys


def family_of(item: str) -> str:
    path = item.split(":", 1)[1]
    for name, pattern in FAMILIES:
        if re.search(pattern, path):
            return name
    return "other"


VOLTAGES = ("ulv", "lv", "mv", "hv", "ev", "iv", "luv", "zpm", "uv", "uhv", "uev", "uiv", "uxv", "opv", "max")
ROWS = ("steam", "lv", "mv", "hv", "ev", "iv", "luv", "zpm", "uv", "uhv")   # uhv: UHV and above
PREFIX = re.compile(r"^[a-z_]+:(" + "|".join(VOLTAGES) + r")_")


def circuit_tiers() -> dict[str, int]:
    """Circuit item -> voltage tier, from the circuits/<tier> item tags of the GregTech mods."""
    lock = json.loads((PACK / "manifest" / "full.lock.json").read_text())
    out: dict[str, int] = {}
    for m in lock["mods"]:
        if m["mod_id"] not in ("gtceu", "gtna", "gtia"):
            continue
        with zipfile.ZipFile(CACHE / m["filename"]) as z:
            for name in z.namelist():
                match = re.fullmatch(r"data/[a-z_]+/tags/items/circuits/([a-z]+)\.json", name)
                if match and match.group(1) in VOLTAGES:
                    for value in json.loads(z.read(name)).get("values", []):
                        if isinstance(value, str) and not value.startswith("#"):
                            out.setdefault(value, VOLTAGES.index(match.group(1)))
    return out


def recipe_tiers(targets: list[str]) -> dict[str, int]:
    """Voltage tier of an item: its tier prefix or circuit tier, else the cheapest recipe that makes it, where a
    recipe counts the voltage it runs at and the highest tier among its ingredients (any one alternative suffices)."""
    import gzip
    makers: dict[str, list[dict]] = {}
    with gzip.open(PACK / "manifest/registry/pack/recipes.jsonl.gz", "rt") as f:
        for line in f:
            recipe = json.loads(line)
            if any(word in recipe["id"] for word in ("macerat", "arc_furnace", "extract", "/recycl", "disassembl")):
                continue
            for part in recipe.get("out", []):
                for item in part.get("item", []):
                    makers.setdefault(item, []).append(recipe)
    circuits = circuit_tiers()
    import fnmatch
    import tomllib
    gathered = tomllib.loads((PACK / "quests-src" / "reachability.toml").read_text())["world"]["items"]
    memo: dict[str, int] = {}
    busy: set[str] = set()

    def tier(item: str, depth: int = 0) -> int:
        if item in memo:
            return memo[item]
        if item in circuits:
            return circuits[item]
        if any(fnmatch.fnmatch(item, pattern) for pattern in gathered):
            return 0  # gathered by hand
        match = PREFIX.match(item)
        if match:
            return VOLTAGES.index(match.group(1))
        if item in busy or depth > 6 or item not in makers:
            return 0
        busy.add(item)
        best = 99
        for recipe in makers[item]:
            eu = max((p.get("eu", 0) for p in recipe.get("tick_in", [])), default=0)
            level = reach.tier_of(eu) if eu else 0
            for slot in recipe.get("in", []):
                options = slot.get("item") or []
                if options:
                    level = max(level, min(tier(o, depth + 1) for o in options))
            best = min(best, level)
        busy.discard(item)
        memo[item] = 0 if best == 99 else best
        return memo[item]

    return {item: tier(item) for item in targets}


def row_of(item: str, level: int) -> str:
    if level <= 0:
        return "steam"
    return ROWS[min(level, len(ROWS) - 1)]


def main() -> int:
    multis = [json.loads(line)["item"] for line in (PACK / "manifest/registry/pack/machines.jsonl").open()
              if json.loads(line).get("multiblock")]
    levels = recipe_tiers(multis)
    tier = {item: row_of(item, levels[item]) for item in multis}
    for row in ROWS:
        print(f"{row}: {sum(1 for t in tier.values() if t == row)} multiblocks")
    tables = lang_tables()
    lines = ["# Generated by tools/multiblock_goals.py from the pack export; rerun it after the export changes.",
             "# tier: the highest voltage the controller's cheapest recipe needs (its own and its parts'); uhv = UHV and up.", ""]
    for item in sorted(multis, key=lambda i: (ROWS.index(tier[i]), family_of(i), i)):
        keys = ", ".join(f'"{k}"' for k in text_keys(item, tables))
        lines.append(f'[[multiblock]]\nitem = "{item}"\ntier = "{tier[item]}"\n'
                     f'family = "{family_of(item)}"\ntext = [{keys}]\n')
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT.relative_to(PACK)}: {len(multis)} multiblocks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
