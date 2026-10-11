#!/usr/bin/env python3
"""Generate and check the GTIA quest book from short specifications.

    questgen.py build    write config/ftbquests/quests/ from quests-src/ (book.toml, one TOML per chapter)
    questgen.py check    structural checks on the generated files
    questgen.py why "<quest title>" i:<item>    why the reachability check says the item is out of reach there
    questgen.py audit "<quest title>" [i:<item> ...]   shortcut audit: what unbooked machines open at that point

A chapter is described in `quests-src/<file>.toml` with the lanes and rows a quest sits on, not with coordinates:

    spine      x = 0       the main path, in hexagons; a quest that gates a recipe is bigger
    materials  x = -3, -4.5 ...   ores, ingots, dusts
    machines   x = 3, 4.5 ...     machines and multiblocks
    outer      x = 7.5 ...        optional extras and hints

Rows are 1.5 apart. Ids are derived from names, so rebuilding never changes an id a player's progress depends on. The Start chapter keeps the author's approved quests: it is read from
`quests-src/start.original.snbt` and only gains shapes, sizes, optional marks, a group, a new quest and a link.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import snbt  # noqa: E402
from snbt import Raw, double, long  # noqa: E402

PACK = Path(__file__).resolve().parents[1]
ROOT = PACK.parent
SRC = PACK / "quests-src"
OUT = PACK / "config" / "ftbquests" / "quests"
REGISTRY = PACK / "manifest" / "registry"

ROW = 1.5
LANES = {"spine": (0.0, 0.0), "materials": (-3.0, -1.5), "machines": (3.0, 1.5), "outer": (7.5, 1.5)}

# role -> FTB Quests presentation
ROLES = {
    "entry": {"shape": "gear", "size": 2.0},
    "exit": {"shape": "gear", "size": 1.5},
    "milestone": {"shape": "gear", "size": 2.25},     # the stops that matter: Steel, the first circuit
    "gate": {"shape": "hexagon", "size": 1.75},       # the key metal of a tier (Aluminium, Kanthal, Titanium...)
    "spine": {"shape": "hexagon", "size": 1.25},      # the main road
    "side": {"shape": "circle", "size": 1.0},
    "detail": {"shape": "circle", "size": 0.75},      # small steps inside a cluster
    "optional": {"shape": "diamond", "size": 1.0, "optional": True},
    "hint": {"shape": "pentagon", "size": 1.25, "optional": True},
    "header": {"shape": "square", "size": 1.25},
    "cell": {"shape": "square", "size": 1.0},
    "gallery": {"shape": "hexagon", "size": 1.5, "optional": True},   # a showcase of machines, GTO style
    "fuel": {"shape": "pentagon", "size": 1.0, "optional": True},
}

# Sizes the chapters not rewritten yet were laid out for (rows 1.5 apart).
LEGACY_SIZES = {"entry": 2.0, "exit": 1.5, "gate": 2.0, "spine": 1.0, "milestone": 2.0, "hint": 1.0, "side": 1.0,
                "optional": 1.0}

# Text colours, following the convention GTO's books use (and that players of those packs already read):
# gold for things you hold, yellow for numbers and key terms, red for warnings, green for good advice,
# light purple for mechanics, grey italics for side notes. Written as [tag]text[/] in the specs.
COLOURS = {"item": "&6", "num": "&e", "warn": "&c", "tip": "&a", "mech": "&d", "note": "&o&7"}


def colour(text: str) -> str:
    out = re.sub(r"\[(\w+)\](.*?)\[/\]", lambda m: COLOURS[m.group(1)] + m.group(2) + "&r", text, flags=re.S)
    if re.search(r"\[/?\w*\]", out):
        raise SystemExit(f"unbalanced or unknown colour tag in: {text[:80]!r}")
    return out


def ident(seed: str) -> str:
    """A stable FTB Quests id. FTB Quests reads ids as signed 64-bit longs, so the top bit must stay zero."""
    value = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16], 16) & 0x7FFFFFFFFFFFFFFF
    return f"{value or 1:016X}"


def pretty(item_id: str) -> str:
    return " ".join(word.capitalize() for word in item_id.split(":", 1)[-1].replace("/", " ").split("_"))


def fuel_table(recipe_type: str, limit: int = 12) -> str:
    """What a generator type burns and how much EU one bucket gives, read from the full-pack recipe export."""
    import gzip
    rows = []
    with gzip.open(REGISTRY / "pack" / "recipes.jsonl.gz", "rt", encoding="utf-8") as lines:
        for line in lines:
            recipe = json.loads(line)
            if recipe["type"] != recipe_type:
                continue
            eu = sum(p.get("eu", 0) for p in recipe.get("tick_out", []) if "eu" in p)
            fluids = [(p["fluid"][0], p["mb"]) for p in recipe.get("in", []) + recipe.get("tick_in", [])
                      if p.get("fluid") and p.get("mb")]
            if eu and len(fluids) == 1:
                fluid, mb = fluids[0]
                rows.append((eu * recipe["duration"] * 1000 // mb, fluid))
    if not rows:
        raise SystemExit(f"fuel_table: no fuel recipes of type {recipe_type} in the export")
    rows.sort(reverse=True)
    best = {}
    for value, fluid in rows:
        best.setdefault(fluid, value)
    lines = ["EU per bucket, from the recipes in this pack:"]
    for fluid, value in list(best.items())[:limit]:
        lines.append(f"&6{pretty(fluid)}&r: {value:,} EU")
    if len(best) > limit:
        lines.append(f"...and {len(best) - limit} more; the recipe viewer lists them all.")
    return "\n".join(lines)


# ------------------------------------------------------------------ chapter spec -> SNBT

def paragraphs(text: str) -> list[str]:
    out: list[str] = []
    text = colour(text)
    for block in re.split(r"\n\s*\n", text.strip()):
        if out:
            out.append("")
        if block.lstrip().startswith(("EU per bucket", "- ")):
            out.extend(line.strip() for line in block.strip().splitlines())  # tables and lists keep their lines
        else:
            out.append(" ".join(block.split()))
    return out


def lane_x(lane: str, col: int) -> float:
    base, step = LANES[lane]
    return base + step * col


def periodic_cell(z: int) -> tuple[float, int]:
    """(group column, row) for an element laid out like the table; the f-block sits on two rows below it."""
    if z == 1:
        return 1, 1
    if z == 2:
        return 18, 1
    for first, last, period, left in ((3, 4, 2, 1), (11, 12, 3, 1), (37, 38, 5, 1), (55, 56, 6, 1), (87, 88, 7, 1)):
        if first <= z <= last:
            return left + (z - first), period
    for first, last, period in ((5, 10, 2), (13, 18, 3)):
        if first <= z <= last:
            return 13 + (z - first), period
    for first, last, period in ((19, 36, 4), (37 + 2, 54, 5), (72, 86, 6), (104, 118, 7)):
        if first <= z <= last:
            start = {4: 1, 5: 3, 6: 4, 7: 4}[period]
            return start + (z - first), period
    if 57 <= z <= 71:
        return 3 + (z - 57), 9
    if 89 <= z <= 103:
        return 3 + (z - 89), 10
    raise ValueError(f"no cell for element {z}")


class Book:
    def __init__(self):
        spec = tomllib.loads((SRC / "book.toml").read_text(encoding="utf-8"))
        self.groups = spec["group"]
        self.chapters = spec["chapter"]
        self.quest_ids: dict[str, str] = {}      # "chapter:key" -> id
        self.specs: dict[str, dict] = {}
        self.reward_tables: dict[str, dict] = {}
        self.allowed_machine_rewards: dict[str, set[str]] = {}
        self.pending: dict[str, str] = {}        # quest id -> why its reachability findings are notes for now
        for chapter in self.chapters:
            if chapter["kind"] == "generated":
                self.specs[chapter["file"]] = tomllib.loads((SRC / f"{chapter['file']}.toml").read_text(encoding="utf-8"))

    def group_id(self, key: str) -> str:
        return ident("group:" + key)

    def chapter_id(self, file: str) -> str:
        if file == "start":
            return snbt.loads((SRC / "start.original.snbt").read_text(encoding="utf-8"))["id"]
        return ident("chapter:" + file)

    def qid(self, file: str, key: str) -> str:
        return ident(f"quest:{file}:{key}")

    def start_quest(self, title: str) -> str:
        start = snbt.loads((SRC / "start.original.snbt").read_text(encoding="utf-8"))
        for quest in start["quests"]:
            if quest.get("title") == title:
                return quest["id"]
        raise KeyError(f"no Start quest titled {title!r}")

    # -- ids for every quest, so dependencies can point across chapters
    def index(self):
        for file, spec in self.specs.items():
            self.quest_ids[f"{file}:entry"] = self.qid(file, "entry")
            if "exit" in spec:
                self.quest_ids[f"{file}:exit"] = self.qid(file, "exit")
            for quest in spec.get("quest", []):
                self.quest_ids[f"{file}:{quest['key']}"] = self.qid(file, quest["key"])

    def resolve(self, file: str, ref: str) -> str:
        if ref.startswith("start/"):
            return self.start_quest(ref.split("/", 1)[1])
        if ":" in ref and ref.split(":", 1)[0] in self.specs:
            return self.quest_ids[ref]
        return self.quest_ids[f"{file}:{ref}"]

    def build_chapter(self, chapter: dict) -> dict:
        file = chapter["file"]
        spec = self.specs[file]
        meta = spec["chapter"]
        quests = []
        positions = []

        def rewards_of(key, reward_specs):
            out = []
            for i, reward in enumerate(reward_specs or []):
                entry = {}
                rid = ident(f"reward:{file}:{key}:{i}")
                if "choice" in reward:
                    table = ident(f"table:{file}:{key}:{i}")
                    self.reward_tables[table] = {
                        "id": table, "loot_size": Raw("1"), "order_index": Raw(str(len(self.reward_tables))),
                        "rewards": [{**({"count": Raw(str(c["count"]))} if c.get("count", 1) > 1 else {}),
                                     "item": c["item"]} for c in reward["choice"]],
                        "title": reward.get("title", "Pick one")}
                    out.append({"id": rid, "table_id": Raw(f"{int(table, 16)}L"), "type": "choice"})
                    continue
                if "xp_levels" in reward:
                    out.append({"id": rid, "type": "xp_levels", "xp_levels": Raw(str(reward["xp_levels"]))})
                    continue
                if reward.get("count", 1) > 1:
                    entry["count"] = Raw(str(reward["count"]))
                entry["id"] = rid
                entry["item"] = reward["item"]
                entry["type"] = "item"
                out.append(entry)
            return out

        def tasks_of(key, task_specs):
            out = []
            for i, task in enumerate(task_specs or []):
                tid = ident(f"task:{file}:{key}:{i}")
                if "item" in task:
                    out.append({"id": tid, "type": "item", "item": task["item"], "count": long(task.get("count", 1)),
                                "consume_items": snbt.boolean(task.get("consume", False)),
                                "match_nbt": snbt.boolean(False)})
                elif "fluid" in task:
                    out.append({"amount": long(task.get("amount", 1000)), "fluid": task["fluid"], "id": tid,
                                "type": "fluid"})
                elif "observe" in task:
                    entry = {"icon": task.get("icon", task["observe"]), "id": tid, "observe_type": Raw("0"),
                             "timer": long(task.get("timer", 0)), "to_observe": task["observe"], "type": "observation"}
                    if task.get("title"):
                        entry["title"] = task["title"]
                    out.append(entry)
                elif "dimension" in task:
                    out.append({"dimension": task["dimension"], "id": tid, "type": "dimension"})
                elif "checkmark" in task:
                    out.append({"id": tid, "type": "checkmark", "title": task["checkmark"]})
                else:
                    raise SystemExit(f"{file}:{key}: unknown task {task}")
            return out

        def extra_of(quest):
            extra = {k: quest[k] for k in ("shape", "size", "optional", "dep_mode", "min_deps", "hide_lines",
                                            "hidden", "allow_machine_reward", "pending") if k in quest}
            if "column" in quest or "x" in quest:
                extra["x"] = quest["x"] if "x" in quest else spec["columns"][quest["column"]]
                extra["y"] = quest["y"] if "y" in quest else spec["rows"][quest["grid_row"]]
            return extra

        def add(key, role, lane, col, row, title, subtitle, text, tasks, deps, icon=None, rewards=None, task_title=None,
                extra=None):
            extra = extra or {}
            style = dict(ROLES[role])
            if chapter.get("legacy") and role in LEGACY_SIZES:
                style["size"] = LEGACY_SIZES[role]
            for field in ("shape", "size", "optional"):
                if field in extra:
                    style[field] = extra[field]
            q = {}
            if deps:
                q["dependencies"] = deps
            if extra.get("dep_mode") == "one":
                q["dependency_requirement"] = "one_completed"
            if extra.get("min_deps"):
                q["min_required_dependencies"] = Raw(str(extra["min_deps"]))
            q["description"] = paragraphs(text)
            if icon:
                q["icon"] = icon
            q["id"] = self.qid(file, key)
            if extra.get("hide_lines"):
                q["hide_dependency_lines"] = Raw("true")
            if extra.get("hidden"):
                q["hide_until_deps_visible"] = Raw("true")
            if style.get("optional"):
                q["optional"] = Raw("true")
            q["rewards"] = rewards_of(key, rewards)
            q["shape"] = style["shape"]
            q["size"] = double(style["size"])
            q["subtitle"] = colour(subtitle)
            q["tasks"] = tasks
            q["title"] = title
            if "x" in extra:
                x, y = extra["x"], extra["y"]
            else:
                x, y = lane_x(lane, col), row * ROW
            q["x"] = double(x)
            q["y"] = double(y)
            quests.append(q)
            positions.append((key, x, y, style["size"]))
            if extra.get("pending"):
                self.pending[q["id"]] = extra["pending"]
            if extra.get("allow_machine_reward"):
                self.allowed_machine_rewards[q["id"]] = set(extra["allow_machine_reward"])

        def check_task(key, label):
            return [{"id": ident(f"task:{file}:{key}:0"), "type": "checkmark", "title": label}]

        # entry
        entry = spec["entry"]
        add("entry", "entry", "spine", 0, 0, meta["title"], entry["subtitle"], entry["text"],
            check_task("entry", entry.get("task", "Begin")), [self.resolve(file, r) for r in entry.get("requires", [])],
            icon=meta["icon"], rewards=entry.get("reward"), extra=extra_of(entry))

        for quest in spec.get("quest", []):
            tasks = tasks_of(quest["key"], quest.get("task", []))
            if not tasks:
                tasks = check_task(quest["key"], quest.get("checkmark", "Read and continue"))
            text = quest["text"]
            if quest.get("fuel_table"):
                text = text.rstrip() + "\n\n" + fuel_table(quest["fuel_table"])
            add(quest["key"], quest.get("role", "side"), quest.get("lane", "spine"), quest.get("col", 0),
                quest.get("row", 0), quest["title"], quest["subtitle"], text, tasks,
                [self.resolve(file, d) for d in quest.get("deps", [])], icon=quest.get("icon"),
                rewards=quest.get("reward"), extra=extra_of(quest))

        exit_spec = spec.get("exit")
        links = []
        nxt = chapter.get("next")
        if exit_spec:
            add("exit", "exit", "spine", 0, exit_spec.get("row", 0), exit_spec["title"], exit_spec["subtitle"], exit_spec["text"],
                tasks_of("exit", exit_spec["task"]) if isinstance(exit_spec.get("task"), list)
                else check_task("exit", exit_spec.get("task", "Ascend")), [self.resolve(file, d) for d in exit_spec["deps"]],
                icon=exit_spec.get("icon", meta["icon"]), rewards=exit_spec.get("reward"), extra=extra_of(exit_spec))
            if nxt:
                if "x" in exit_spec:  # free layout: the link sits next to the exit, along the road
                    lx, ly = exit_spec["x"] + 2.0, exit_spec["y"]
                else:
                    lx, ly = 0.0, (exit_spec["row"] + 2) * ROW
                links.append({"id": ident(f"link:{file}:{nxt}"), "linked_quest": self.qid(nxt, "entry"),
                              "shape": "gear", "size": double(1.5), "x": double(lx), "y": double(ly)})
        return {
            "default_hide_dependency_lines": Raw("false"),
            "default_quest_shape": "circle",
            "filename": file,
            "group": self.group_id(chapter["group"]),
            "icon": meta["icon"],
            "id": self.chapter_id(file),
            "order_index": Raw(str(chapter["order"])),
            "quest_links": links,
            "quests": quests,
            "title": meta["title"],
        }, positions

    # -- Start: the author's approved chapter, plus presentation and a link onward
    def build_start(self, chapter: dict) -> dict:
        start = snbt.loads((SRC / "start.original.snbt").read_text(encoding="utf-8"))
        meta = tomllib.loads((SRC / "start.toml").read_text(encoding="utf-8"))
        roles = meta["roles"]
        for quest in start["quests"]:
            role = roles.get(quest["title"])
            if role is None:
                raise SystemExit(f"start.toml has no role for the Start quest {quest['title']!r}")
            if role == "keep":
                continue
            style = ROLES[role]
            quest["shape"] = style["shape"]
            quest["size"] = double(LEGACY_SIZES.get(role, style["size"]))  # the approved Start keeps its sizes
            if style.get("optional"):
                quest["optional"] = Raw("true")
            else:
                quest.pop("optional", None)
        for new in meta.get("new_quest", []):
            style = ROLES[new["role"]]
            quest = {"dependencies": [self.start_quest(new["after"])], "description": paragraphs(new["text"]),
                     "id": ident("quest:start:" + new["key"])}
            if style.get("optional"):
                quest["optional"] = Raw("true")
            quest["shape"] = style["shape"]
            quest["size"] = double(LEGACY_SIZES.get(new["role"], style["size"]))
            quest["subtitle"] = new["subtitle"]
            quest["tasks"] = [{"id": ident("task:start:" + new["key"]), "type": "checkmark", "title": new["task"]}]
            quest["title"] = new["title"]
            quest["x"] = double(new["x"])
            quest["y"] = double(new["y"])
            if new.get("icon"):
                quest["icon"] = new["icon"]
            start["quests"].append(quest)
        start["group"] = self.group_id(chapter["group"])
        start["order_index"] = Raw(str(chapter["order"]))
        nxt = chapter.get("next")
        if nxt:
            start["quest_links"] = [{"id": ident(f"link:start:{nxt}"), "linked_quest": self.qid(nxt, "entry"),
                                     "shape": "gear", "size": double(1.5), "x": double(0.0), "y": double(meta["link_y"])}]
        return start

    # -- Periodic Table: one quest per element, laid out like the table, built from the registry export
    def build_periodic(self, chapter: dict) -> dict:
        rows = [line.split("\t") for line in (REGISTRY / "elements.tsv").read_text(encoding="utf-8").splitlines()[1:]]
        by_z: dict[int, list[str]] = {}
        for row in rows:
            z = int(row[0])
            if 1 <= z <= 118 and not re.search(r"_\d+$", row[3]) and row[3].split(":")[1] not in ("deuterium", "tritium"):
                by_z.setdefault(z, row)
        quests = []
        for z in sorted(by_z):
            _, symbol, name, material, ingot, dust, gem, bucket = by_z[z]
            item = ingot or gem or dust or bucket
            # Many heavy elements exist only as a material with no item; those cells are checked off by hand.
            group, period = periodic_cell(z)
            symbol = re.sub(r"-\d+$", "", symbol)
            quests.append({
                "description": paragraphs(f"Produce {pretty(item)}. {name} has atomic number {z}." if item
                                          else f"{name} has atomic number {z}. It has no item in the pack yet, so check it off yourself."),
                "icon": item or "minecraft:paper",
                "id": ident(f"quest:periodic:{z}"),
                "optional": Raw("true"),
                "rewards": [],
                "shape": "circle",
                "size": double(1.0),
                "subtitle": f"{symbol} - {z}",
                "tasks": [({"id": ident(f"task:periodic:{z}"), "type": "item", "item": item, "count": long(1),
                            "consume_items": snbt.boolean(False), "match_nbt": snbt.boolean(False)} if item else
                           {"id": ident(f"task:periodic:{z}"), "type": "checkmark"})],
                "title": name,
                "x": double((group - 9.5) * ROW),
                "y": double(period * ROW),
            })
        meta = tomllib.loads((SRC / "periodic.toml").read_text(encoding="utf-8"))["chapter"]
        return {
            "default_hide_dependency_lines": Raw("false"),
            "default_quest_shape": "circle",
            "filename": chapter["file"],
            "group": self.group_id(chapter["group"]),
            "icon": meta["icon"],
            "id": self.chapter_id(chapter["file"]),
            "order_index": Raw(str(chapter["order"])),
            "quest_links": [],
            "quests": quests,
            "title": meta["title"],
        }

    def build(self):
        self.index()
        chapters_out = {}
        for chapter in self.chapters:
            if chapter["kind"] == "migrated":
                chapters_out[chapter["file"]] = self.build_start(chapter)
            elif chapter["kind"] == "periodic":
                chapters_out[chapter["file"]] = self.build_periodic(chapter)
            else:
                chapters_out[chapter["file"]] = self.build_chapter(chapter)[0]
        self.reduce_dependencies(chapters_out)
        return chapters_out

    def reduce_dependencies(self, chapters_out) -> None:
        """Drop a dependency another dependency already implies (A needs B and C, C needs B: A keeps only C).
        FTB Quests unlocks the same quests either way, and the chapter loses the lines that cross it end to end,
        such as a prerequisite from the top of the tier. Only all-of dependencies in rewritten
        chapters are reduced; "any one of" lists keep every entry."""
        quests = {q["id"]: q for c in chapters_out.values() for q in c["quests"]}
        memo: dict[str, set[str]] = {}

        def ancestors(qid):
            if qid not in memo:
                memo[qid] = set()
                for dep in quests.get(qid, {}).get("dependencies", []):
                    memo[qid] |= {dep} | ancestors(dep)
            return memo[qid]

        reducible = {c["file"] for c in self.chapters if c["kind"] == "generated" and not c.get("legacy")}
        for file in reducible:
            for q in chapters_out[file]["quests"]:
                deps = q.get("dependencies", [])
                if len(deps) < 2 or q.get("dependency_requirement"):
                    continue
                keep = [d for d in deps if not any(d in ancestors(o) for o in deps if o != d)]
                q["dependencies"] = keep

    def groups_snbt(self):
        return {"chapter_groups": [{"id": self.group_id(g["key"]), "title": g["title"]} for g in self.groups]}


# ------------------------------------------------------------------ commands

def load_registry():
    """(item ids, namespaces) from manifest/registry, or (None, None) when there is no export."""
    path = REGISTRY / "items.txt"
    if not path.exists():
        return None, None
    items = set(path.read_text(encoding="utf-8").split())
    return items, {item.split(":", 1)[0] for item in items}


def check_reward_rules(book, quests_by_id, chapter_of, all_ids, errors) -> None:
    """Rewards in the generated chapters never give more than a stack. (What a reward may give at that point of the
    book is the reachability check's job.)"""
    generated = {c["file"] for c in book.chapters if c["kind"] == "generated"}
    for qid, q in quests_by_id.items():
        if chapter_of[qid] not in generated:
            continue
        for reward in q.get("rewards", []):
            item = reward.get("item")
            if isinstance(item, str) and snbt.number(reward.get("count", "1")) > 64:
                errors.append(f"{all_ids[qid]}: rewards more than a stack of {item}")


MAX_LINE = 5.0  # longer dependency lines read as noise; hide them or move the quests closer


def check_layout(book, quests_by_id, chapter_of, errors) -> None:
    """The drawn dependency lines of a rewritten chapter must not cross, run over another quest or run across the
    whole chapter. (The approved Start, the Periodic Table and the chapters not rewritten yet are left out.)"""
    import math
    checked = {c["file"] for c in book.chapters if c["kind"] == "generated" and not c.get("legacy")}
    for file in sorted(checked):
        quests = {qid: q for qid, q in quests_by_id.items() if chapter_of[qid] == file}
        pos = {qid: (snbt.number(q["x"]), snbt.number(q["y"]), snbt.number(q.get("size", "1.0d"))) for qid, q in quests.items()}
        lines = []
        for qid, q in quests.items():
            if q.get("hide_dependency_lines") == "true":
                continue
            for dep in q.get("dependencies", []):
                if dep in quests:
                    lines.append((dep, qid))
        title = lambda qid: quests[qid].get("title", qid)
        for a, b in lines:
            (ax, ay, _), (bx, by, _) = pos[a][:3], pos[b][:3]
            length = math.hypot(bx - ax, by - ay)
            if length > MAX_LINE:
                errors.append(f"{file}: line {title(a)!r} -> {title(b)!r} is {length:.1f} long (max {MAX_LINE})")
            for c, (cx, cy, size) in pos.items():
                if c in (a, b) or length == 0:
                    continue
                u = max(0.0, min(1.0, ((cx - ax) * (bx - ax) + (cy - ay) * (by - ay)) / length ** 2))
                if math.hypot(ax + u * (bx - ax) - cx, ay + u * (by - ay) - cy) < size * 0.45:
                    errors.append(f"{file}: line {title(a)!r} -> {title(b)!r} runs over {title(c)!r}")

        def cross(p1, p2, p3, p4):
            d = lambda a, b, c: (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            return (d(p3, p4, p1) * d(p3, p4, p2) < 0) and (d(p1, p2, p3) * d(p1, p2, p4) < 0)
        for i, (a, b) in enumerate(lines):
            for c, d_ in lines[i + 1:]:
                if {a, b} & {c, d_}:
                    continue
                if cross(pos[a][:2], pos[b][:2], pos[c][:2], pos[d_][:2]):
                    errors.append(f"{file}: lines {title(a)!r} -> {title(b)!r} and {title(c)!r} -> {title(d_)!r} cross")


def check_reachability(book, quests_by_id, chapter_of, all_ids, errors, notes) -> None:
    """Can the player do each task, and get each reward, at that point of the book? (tools/reach.py)

    Findings in the generated chapters are errors. The Start chapter belongs to the author: its findings are notes.
    The Periodic Table is a reference with no order, so it is left out.
    """
    import reach
    if not reach.available():
        notes.append("reachability not checked: run `tools/server_smoke.py --export-recipes` first")
        return
    book.build()  # fills allowed_machine_rewards
    legacy = {c["file"] for c in book.chapters if c.get("legacy")}
    quests = {qid: q for qid, q in quests_by_id.items() if chapter_of[qid] != "periodic"}
    for qid, q in quests.items():
        q["_allow_machine_reward"] = sorted(book.allowed_machine_rewards.get(qid, ()))
    for qid, message in reach.check(quests, all_ids):
        if not qid:
            notes.append(message.removeprefix("note: "))
        elif chapter_of[qid] == "start":
            notes.append(f"{all_ids[qid]} (author's chapter, not changed): {message}")
        elif qid in book.pending:
            notes.append(f"{all_ids[qid]} (pending: {book.pending[qid]}): {message}")
        elif chapter_of[qid] in legacy:
            notes.append(f"{all_ids[qid]} (chapter not rewritten yet): {message}")
        else:
            errors.append(f"{all_ids[qid]}: {message}")


LANG_SRC = SRC / "lang"
LANG_PACK = PACK / "config" / "openloader" / "resources" / "gtia_quests"
LANGUAGES = ("pt_br", "zh_cn")


def translatable(line: str) -> bool:
    """Plain text lines get a key; empty lines and FTB tags such as {image:...} or {@pagebreak} stay as they are."""
    stripped = line.strip()
    return bool(stripped) and not (stripped.startswith("{") and stripped.endswith("}"))


def localize(chapters: dict[str, dict], groups: dict) -> dict[str, str]:
    """Replaces every player-facing text with a {key} that FTB Quests translates, and returns the English text."""
    english: dict[str, str] = {}

    def key(name: str, text: str) -> str:
        english[name] = text
        return "{" + name + "}"

    for data in chapters.values():
        chapter_id = data["id"]
        if data.get("title"):
            data["title"] = key(f"gtia.quest.chapter.{chapter_id}", data["title"])
        if data.get("subtitle"):
            data["subtitle"] = [key(f"gtia.quest.chapter.{chapter_id}.subtitle.{i}", line) if translatable(line)
                                else line for i, line in enumerate(data["subtitle"])] \
                if isinstance(data["subtitle"], list) else key(f"gtia.quest.chapter.{chapter_id}.subtitle",
                                                               data["subtitle"])
        for quest in data["quests"]:
            base = f"gtia.quest.{quest['id']}"
            for field in ("title", "subtitle"):
                if quest.get(field):
                    quest[field] = key(f"{base}.{field}", quest[field])
            if quest.get("description"):
                quest["description"] = [key(f"{base}.desc.{i}", line) if translatable(line) else line
                                        for i, line in enumerate(quest["description"])]
            for task in quest.get("tasks", []):
                if task.get("title"):
                    task["title"] = key(f"{base}.task.{task['id']}", task["title"])
            for reward in quest.get("rewards", []):
                if reward.get("title"):
                    reward["title"] = key(f"{base}.reward.{reward['id']}", reward["title"])
    for group in groups["chapter_groups"]:
        group["title"] = key(f"gtia.quest.group.{group['id']}", group["title"])
    return english


def write_languages(english: dict[str, str]) -> None:
    """en_us from the source text; other languages from quests-src/lang/<lang>.json ({English text: translation})."""
    lang_dir = LANG_PACK / "assets" / "gtia_quests" / "lang"
    lang_dir.mkdir(parents=True, exist_ok=True)
    (LANG_PACK / "pack.mcmeta").write_text(json.dumps(
        {"pack": {"description": "GTIA quest book text", "pack_format": 15}}, indent=2) + "\n", encoding="utf-8")
    (lang_dir / "en_us.json").write_text(json.dumps(english, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for lang in LANGUAGES:
        source = LANG_SRC / f"{lang}.json"
        table = json.loads(source.read_text(encoding="utf-8")) if source.exists() else {}
        missing = sorted({text for text in english.values() if text not in table})
        translated = {name: table.get(text, text) for name, text in english.items()}
        (lang_dir / f"{lang}.json").write_text(json.dumps(translated, ensure_ascii=False, indent=1) + "\n",
                                               encoding="utf-8")
        print(f"wrote lang/{lang}.json ({len(english) - sum(1 for t in english.values() if t not in table)}"
              f"/{len(english)} translated)")
        (LANG_SRC / f"{lang}.missing.json").write_text(
            json.dumps({text: "" for text in missing}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8") \
            if missing else (LANG_SRC / f"{lang}.missing.json").unlink(missing_ok=True)


def cmd_build() -> int:
    book = Book()
    chapters = book.build()
    groups = book.groups_snbt()
    english = localize(chapters, groups)
    write_languages(english)
    chapters_dir = OUT / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    for file, data in chapters.items():
        (chapters_dir / f"{file}.snbt").write_text(snbt.dumps(data), encoding="utf-8")
        print(f"wrote chapters/{file}.snbt ({len(data['quests'])} quests)")
    tables_dir = OUT / "reward_tables"
    if tables_dir.exists():
        for old in tables_dir.glob("*.snbt"):
            old.unlink()
    if book.reward_tables:
        tables_dir.mkdir(parents=True, exist_ok=True)
        for table_id, table in book.reward_tables.items():
            (tables_dir / f"{table_id.lower()}.snbt").write_text(snbt.dumps(table), encoding="utf-8")
        print(f"wrote {len(book.reward_tables)} reward table(s)")
    text = "{\n\tchapter_groups: [\n" + "\n".join(
        f'\t\t{{ id: "{g["id"]}", title: "{g["title"]}" }}' for g in groups["chapter_groups"]) + "\n\t]\n}\n"
    (OUT / "chapter_groups.snbt").write_text(text, encoding="utf-8")
    print(f"wrote chapter_groups.snbt ({len(groups['chapter_groups'])} groups)")
    return cmd_check()


def cmd_check() -> int:
    errors: list[str] = []
    book = Book()
    book.index()
    all_ids: dict[str, str] = {}
    quests_by_id: dict[str, dict] = {}
    chapter_of: dict[str, str] = {}
    registry_items, registry_namespaces = load_registry()
    unchecked_items: set[str] = set()

    def check_item(item_id: str, where: str) -> None:
        if registry_items is None or not isinstance(item_id, str) or ":" not in item_id:
            return
        namespace = item_id.split(":", 1)[0]
        if namespace not in registry_namespaces:
            unchecked_items.add(item_id)
        elif item_id not in registry_items:
            errors.append(f"{where}: item {item_id} does not exist in the registry export")

    def check_id(value: str, where: str) -> None:
        # FTB Quests parses ids with Long.parseLong(hex, 16): anything above 7FFF... throws and the book fails to load.
        if not re.fullmatch(r"[0-9A-F]{16}", value) or int(value, 16) > 0x7FFFFFFFFFFFFFFF or int(value, 16) == 0:
            errors.append(f"{where}: id {value} is not a positive 64-bit hex id FTB Quests can read")

    chapter_files = sorted((OUT / "chapters").glob("*.snbt"))
    for path in chapter_files:
        chapter = snbt.loads(path.read_text(encoding="utf-8"))
        positions = []
        for q in chapter["quests"]:
            where = f"{path.stem}: {q.get('title', q['id'])}"
            check_id(q["id"], where)
            chapter_of[q["id"]] = path.stem
            if q["id"] in all_ids:
                errors.append(f"{where}: duplicate id {q['id']} (also {all_ids[q['id']]})")
            all_ids[q["id"]] = where
            quests_by_id[q["id"]] = q
            if not q.get("title") or not q.get("description"):
                errors.append(f"{where}: missing title or description")
            if any("TODO" in line for line in q.get("description", [])):
                errors.append(f"{where}: unfinished text")
            for reward in q.get("rewards", []):
                check_id(reward["id"], where)
                check_item(reward.get("item"), where)
            for task in q["tasks"]:
                check_id(task["id"], where)
                if task["id"] in all_ids and all_ids[task["id"]] != where:
                    errors.append(f"{where}: duplicate task id {task['id']}")
                all_ids[task["id"]] = where
                item = task.get("item")
                check_item(item, where)
                if isinstance(item, str) and not re.fullmatch(r"[a-z0-9_.-]+:[a-z0-9_./-]+", item):
                    errors.append(f"{where}: malformed item id {item!r}")
            positions.append((q.get("title"), snbt.number(q["x"]), snbt.number(q["y"]), snbt.number(q.get("size", "1.0d"))))
        for i, (a, ax, ay, asize) in enumerate(positions):
            for b, bx, by, bsize in positions[i + 1:]:
                reach = (asize + bsize) / 2
                if abs(ax - bx) < reach and abs(ay - by) < reach:
                    errors.append(f"{path.stem}: {a!r} and {b!r} overlap")
    for qid, q in quests_by_id.items():
        for dep in q.get("dependencies", []):
            if dep not in quests_by_id:
                errors.append(f"{all_ids[qid]}: depends on an unknown quest {dep}")
    # cycles
    state: dict[str, int] = {}

    def visit(qid, trail):
        if state.get(qid) == 2:
            return
        if state.get(qid) == 1:
            errors.append("dependency cycle through " + " -> ".join(all_ids[t] for t in trail + [qid]))
            return
        state[qid] = 1
        for dep in quests_by_id[qid].get("dependencies", []):
            if dep in quests_by_id:
                visit(dep, trail + [qid])
        state[qid] = 2

    for qid in quests_by_id:
        visit(qid, [])
    # links point at real quests
    for path in chapter_files:
        chapter_data = snbt.loads(path.read_text(encoding="utf-8"))
        check_id(chapter_data["id"], f"{path.stem} (chapter)")
        for link in chapter_data.get("quest_links", []):
            check_id(link["id"], f"{path.stem} (link)")
            if link["linked_quest"] not in quests_by_id:
                errors.append(f"{path.stem}: link to an unknown quest {link['linked_quest']}")
    check_reward_rules(book, quests_by_id, chapter_of, all_ids, errors)
    notes: list[str] = []
    check_reachability(book, quests_by_id, chapter_of, all_ids, errors, notes)
    check_layout(book, quests_by_id, chapter_of, errors)
    for line in errors:
        print("ERROR:", line)
    for line in notes:
        print("note:", line)
    if unchecked_items:
        pack_items = set((REGISTRY / "pack" / "items.txt").read_text(encoding="utf-8").split()) \
            if (REGISTRY / "pack" / "items.txt").exists() else set()
        missing = sorted(i for i in unchecked_items if i not in pack_items)
        print(f"note: {len(unchecked_items)} item id(s) from mods outside the core registry: "
              + ", ".join(sorted(unchecked_items)))
        for item in missing:
            errors.append(f"item {item} does not exist in the full-pack export either")
            print("ERROR:", errors[-1])
    total = len(quests_by_id)
    if not errors:
        print(f"OK: {len(chapter_files)} chapters, {total} quests")
    return 1 if errors else 0


def cmd_why(title: str, token: str) -> int:
    """Explain why `token` (i:<item> or f:<fluid>) is out of reach right before the quest titled `title`."""
    import reach
    book = Book()
    book.index()
    quests, names = {}, {}
    for path in sorted((OUT / "chapters").glob("*.snbt")):
        if path.stem == "periodic":
            continue
        for q in snbt.loads(path.read_text(encoding="utf-8"))["quests"]:
            quests[q["id"]] = q
            names[q["id"]] = f"{path.stem}: {q.get('title')}"
    target = [qid for qid, name in names.items() if name.endswith(": " + title) or name == title]
    if len(target) != 1:
        print(f"{len(target)} quests match {title!r}")
        return 1
    for _qid, state in reach.check(quests, names, stop_at=target[0]):
        if isinstance(state, reach.State):
            print("\n".join(reach.explain(state, token, depth=4)))
    return 0


def cmd_audit(title: str, items: list[str]) -> int:
    """Shortcut audit right before the quest titled `title`: machines the book does not ask for yet but the player can
    build, how much each opens, and (for each given i:/f: token) the route they open to it."""
    import reach
    book = Book()
    book.index()
    quests, names = {}, {}
    for path in sorted((OUT / "chapters").glob("*.snbt")):
        if path.stem == "periodic":
            continue
        for q in snbt.loads(path.read_text(encoding="utf-8"))["quests"]:
            quests[q["id"]] = q
            names[q["id"]] = f"{path.stem}: {q.get('title')}"
    target = [qid for qid, name in names.items() if name.endswith(": " + title) or name == title]
    if len(target) != 1:
        print(f"{len(target)} quests match {title!r}")
        return 1
    state = next(s for _q, s in reach.check(quests, names, stop_at=target[0])
                 if isinstance(s, reach.State))
    full, opened = reach.unbooked_surface(state)
    book_items = {t.get("item") for q in quests.values() for t in q["tasks"]}
    print("Machines the player can build here that open new things (not in the book marked *):")
    for machine, count in sorted(opened.items(), key=lambda kv: -kv[1]):
        print(f"  {'*' if machine not in book_items else ' '} {machine:48s} +{count}")
    gained = [full.m.names[t] for t, v in enumerate(full.have) if v and not state.have[t]
              and full.m.names[t].startswith(("i:", "f:", "p:"))]
    print(f"{len(gained)} items, fluids or power tiers become reachable that the book has not led to yet.")
    for token in items:
        print("\n".join(reach.derivation(full, token, stop=state, limit=7)) or f"{token}: not reachable even so")
    return 0


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "audit":
        return cmd_audit(sys.argv[2], sys.argv[3:])
    if len(sys.argv) == 4 and sys.argv[1] == "why":
        return cmd_why(sys.argv[2], sys.argv[3])
    if len(sys.argv) != 2 or sys.argv[1] not in ("build", "check"):
        print(__doc__)
        return 2
    return cmd_build() if sys.argv[1] == "build" else cmd_check()


if __name__ == "__main__":
    sys.exit(main())
