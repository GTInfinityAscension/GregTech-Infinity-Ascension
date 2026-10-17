"""Reachability: can the player make this item at this point of the quest book?

The model is built from the full-pack export (`server_smoke.py --export-recipes`, in manifest/registry/pack/) and
from quests-src/reachability.toml. A *token* is something the player can have:

    i:<item>          an item                     f:<fluid>         a fluid
    p:<tier>          electric power of that tier (0 ULV, 1 LV ...)
    c:<type>:<tier>   a machine that runs recipe type <type> at that tier; c:<type>:free runs recipes without EU
    q:<item>          a machine the book has introduced: an earlier quest asked for it or gave it

A machine only works for the check once the book has introduced it (q:). Without that rule every pre-Aluminium item
would count as reachable from the first minute, because the player *could* craft any machine; the question the
check answers is narrower: has the book led the player to the machine this step needs? Hand crafting and the
vanilla furnace are always there.

Every recipe becomes a rule "all of these slots -> these outputs", where a slot is satisfied by any one of its
tokens (an ingredient tag, or the machines able to run the recipe). Machines, generators, boilers and buckets add
rules of their own. `State` holds what is reachable and grows by forward chaining when tokens are added.

The check walks the book in dependency order. Before a quest the player has the world, plus everything every
ancestor quest asked for or gave, closed under the rules; with `one_completed`/`one_started`, only what all the
alternatives share. A quest then may only ask for what is reachable before it, and only give what is reachable
once its own tasks are done.

Limits: structures are not checked (a multiblock counts once its controller is held), nor are recipe chances,
amounts, rates, biome or weather conditions, and loot. A rule that needs a mod-specific mechanic stays out.
"""

from __future__ import annotations

import fnmatch
import gzip
import json
import tomllib
from array import array
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
EXPORT = PACK / "manifest" / "registry" / "pack"
CONFIG = PACK / "quests-src" / "reachability.toml"
STEAM = "f:gtceu:steam"
MAX_TIER = 14
STEAM_TIER = 1  # GTCEu steam machines refuse recipes above LV


def tier_of(eu: int) -> int:
    tier = 0
    while tier < MAX_TIER and 8 * 4 ** tier < eu:
        tier += 1
    return tier


def available() -> bool:
    return all((EXPORT / name).exists() for name in ("recipes.jsonl.gz", "machines.jsonl", "worldgen.jsonl",
                                                     "items.txt", "fluids.txt"))


class Model:
    def __init__(self):
        config = tomllib.loads(CONFIG.read_text(encoding="utf-8"))
        self.items = set((EXPORT / "items.txt").read_text(encoding="utf-8").split())
        self.fluids = set((EXPORT / "fluids.txt").read_text(encoding="utf-8").split())
        self.machines = [json.loads(line) for line in open(EXPORT / "machines.jsonl", encoding="utf-8")]
        self.machine_items = {m["item"] for m in self.machines}
        self.worldgen = [json.loads(line) for line in open(EXPORT / "worldgen.jsonl", encoding="utf-8")]
        self.tok: dict[str, int] = {}
        self.names: list[str] = []
        self.rules: list[tuple[list[tuple[int, ...]], list[int], str]] = []
        recipes = [json.loads(line) for line in gzip.open(EXPORT / "recipes.jsonl.gz", "rt", encoding="utf-8")]

        # which recipe types produce EU, and what each type consumes (a generator or boiler needs one of them)
        generator_types, fuel = set(), {}
        for recipe in recipes:
            if any("eu" in part for part in recipe.get("tick_out", [])):
                generator_types.add(recipe["type"])
            if recipe["type"].startswith("gtceu:") or recipe["type"].startswith("gtna:"):
                fuel.setdefault(recipe["type"], set()).update(self.slot_tokens(recipe.get("in", []) +
                                                                               recipe.get("tick_in", [])))
        free_types = {r["type"] for r in recipes}
        for recipe in recipes:
            if self.recipe_eu(recipe):
                free_types.discard(recipe["type"])
        multiblock_tiers = config.get("generators", {})
        steam_any_eu = set(config.get("steam_any_eu", {}).get("machines", []))
        self.unknown_generators: list[str] = []

        for machine in self.machines:
            item = "q:" + machine["item"]
            types = machine["types"]
            path = machine["item"].split(":", 1)[1]
            if set(types) & generator_types:
                tier = machine["tier"]
                if machine["multiblock"]:
                    tier = multiblock_tiers.get(machine["item"])
                    if tier is None:
                        self.unknown_generators.append(machine["item"])
                        tier = 1
                fuels = set().union(*(fuel.get(t, set()) for t in types))
                if fuels:
                    self.rule([(item,), tuple(sorted(fuels))], [f"p:{k}" for k in range(tier + 1)], "generator")
                continue
            if set(types) & {"gtceu:steam_boiler", "gtceu:large_boiler"} or "boiler" in path:
                slots = [(item,), ("f:minecraft:water",)]
                fuels = set().union(*(fuel.get(t, set()) for t in types))
                if "solar" not in path and fuels:
                    slots.append(tuple(sorted(fuels)))
                self.rule(slots, [STEAM], "boiler")
                continue
            for recipe_type in types:
                if "steam" in path or path.startswith(("lp_", "hp_")):
                    top = MAX_TIER if machine["item"] in steam_any_eu else STEAM_TIER
                    self.rule([(item,), (STEAM,)], [f"c:{recipe_type}:free"] +
                              [f"c:{recipe_type}:{k}" for k in range(top + 1)], "steam machine")
                elif recipe_type in free_types or (machine["multiblock"] and machine["tier"] == 0
                                                   and recipe_type in free_types):
                    self.rule([(item,)], [f"c:{recipe_type}:free"], "primitive machine")
                else:
                    top = MAX_TIER if machine["multiblock"] else machine["tier"]
                    for k in range(top + 1):
                        # A multiblock adds up its energy hatches (GTCEu EnergyContainerList): two hatches of
                        # tier k feed recipes of tier k + 1, as in the classic two-LV-hatch Electric Blast Furnace.
                        made = [f"c:{recipe_type}:{k}"] + ([f"c:{recipe_type}:free"] if k == 0 else [])
                        if machine["multiblock"] and 1 <= k < MAX_TIER:
                            made.append(f"c:{recipe_type}:{k + 1}")
                        self.rule([(item,), (f"p:{k}",)], made, "electric machine")

        # buckets carry fluids
        for fluid in self.fluids:
            namespace, name = fluid.split(":", 1)
            bucket = f"{namespace}:{name}_bucket"
            if bucket in self.items:
                self.rule([("i:minecraft:bucket",), ("f:" + fluid,)], ["i:" + bucket], "fill bucket")
                self.rule([("i:" + bucket,)], ["f:" + fluid], "empty bucket")

        type_machines = config.get("types", {})
        for recipe in recipes:
            slots = [tuple(sorted(s)) for s in self.ingredient_slots(recipe)]
            recipe_type = recipe["type"]
            if recipe_type in type_machines:
                if type_machines[recipe_type]:
                    slots.append(tuple("i:" + m for m in type_machines[recipe_type]))
            else:
                eu = self.recipe_eu(recipe)
                slots.append((f"c:{recipe_type}:{tier_of(eu)}" if eu else f"c:{recipe_type}:free",))
            outputs = [o for part in ("out", "tick_out") for o in self.output_tokens(recipe.get(part, []))]
            if outputs and all(slots):
                self.rule(slots, outputs, recipe["id"])

        self.world_dimensions = list(config["world"]["dimensions"])
        self.world_items = config["world"]["items"]
        self.world_fluids = config["world"]["fluids"]

    # -- recipe parsing
    @staticmethod
    def recipe_eu(recipe: dict) -> int:
        return sum(part.get("eu", 0) * part.get("amps", 1) for part in recipe.get("tick_in", []))

    @staticmethod
    def slot_tokens(parts: list[dict]) -> set[str]:
        out = set()
        for part in parts:
            out.update("i:" + i for i in part.get("item", []))
            out.update("f:" + f for f in part.get("fluid", []))
        return out

    @staticmethod
    def ingredient_slots(recipe: dict) -> list[set[str]]:
        slots = []
        for part in recipe.get("in", []) + recipe.get("tick_in", []):
            if "eu" in part:
                continue
            if "circuit" in part:
                slots.append({"i:gtceu:programmed_circuit"})
            elif "item" in part:
                slots.append({"i:" + i for i in part["item"]})
            elif "fluid" in part:
                slots.append({"f:" + f for f in part["fluid"]})
            else:
                slots.append({"cap:" + part.get("cap", "?")})  # never available: CWU and the like
        return slots

    @staticmethod
    def output_tokens(parts: list[dict]) -> list[str]:
        out = []
        for part in parts:
            out.extend("i:" + i for i in part.get("item", [])[:1])
            out.extend("f:" + f for f in part.get("fluid", [])[:1])
        return out

    # -- token and rule tables
    def t(self, name: str) -> int:
        index = self.tok.get(name)
        if index is None:
            index = self.tok[name] = len(self.names)
            self.names.append(name)
        return index

    def rule(self, slots, outputs, label) -> None:
        self.rules.append(([tuple(self.t(x) for x in slot) for slot in slots], [self.t(o) for o in outputs], label))

    def compile(self) -> None:
        self.index: list[list[tuple[int, int]]] = [[] for _ in self.names]
        self.offset = array("i")
        self.slots_count = array("i")
        position = 0
        for r, (slots, _outputs, _label) in enumerate(self.rules):
            self.offset.append(position)
            self.slots_count.append(len(slots))
            for s, slot in enumerate(slots):
                for token in slot:
                    self.index[token].append((r, position + s))
            position += len(slots)
        self.total_slots = position
        self.no_slot_rules = [r for r, (slots, _o, _l) in enumerate(self.rules) if not slots]

    def world_seed(self, dimensions) -> list[str]:
        seeds = []
        for pattern in self.world_items:
            seeds.extend("i:" + i for i in fnmatch.filter(self.items, pattern))
        seeds.extend("f:" + f for f in self.world_fluids)
        for entry in self.worldgen:
            if not set(entry["dimensions"]) & set(dimensions):
                continue
            if "fluid" in entry and entry["fluid"]:
                seeds.append("f:" + entry["fluid"])  # a fluid drilling rig still has to be reachable
            for material in entry.get("materials", []):
                namespace, name = material.split(":", 1)
                for item in (f"{namespace}:raw_{name}", f"{namespace}:{name}_ore"):
                    if item in self.items:
                        seeds.append("i:" + item)
            seeds.extend("i:" + b for b in entry.get("blocks", []) if b in self.items)
        return seeds


class State:
    """Reachable tokens, closed under the model's rules."""

    def __init__(self, model: Model, other: State | None = None):
        self.m = model
        if other is None:
            self.have = bytearray(len(model.names))
            self.sat = bytearray(model.total_slots)
            self.missing = array("i", model.slots_count)
            self.why: dict[int, int] = {}
            for r in model.no_slot_rules:
                self.add_tokens(model.rules[r][1])
        else:
            self.have = bytearray(other.have)
            self.sat = bytearray(other.sat)
            self.missing = array("i", other.missing)
            self.why = dict(other.why)

    def add(self, names) -> None:
        self.add_tokens([self.m.tok[n] for n in names if n in self.m.tok])

    def add_tokens(self, tokens) -> None:
        have, sat, missing, index, rules = self.have, self.sat, self.missing, self.m.index, self.m.rules
        stack = [t for t in tokens if t < len(have) and not have[t]]
        while stack:
            token = stack.pop()
            if have[token]:
                continue
            have[token] = 1
            for r, flat in index[token]:
                if sat[flat]:
                    continue
                sat[flat] = 1
                missing[r] -= 1
                if missing[r] == 0:
                    for o in rules[r][1]:
                        if not have[o]:
                            stack.append(o)
                            self.why.setdefault(o, r)

    def union(self, other: State) -> None:
        self.add_tokens([t for t, v in enumerate(other.have) if v and not self.have[t]])

    def has(self, name: str) -> bool:
        index = self.m.tok.get(name)
        return index is not None and index < len(self.have) and bool(self.have[index])

    def tokens(self) -> set[int]:
        return {t for t, v in enumerate(self.have) if v}


def quest_content(quest: dict) -> tuple[list[str], list[str]]:
    """(what the quest asks the player to hold, what it gives) as tokens."""
    tasks, rewards = [], []
    for task in quest.get("tasks", []):
        kind = task.get("type")
        item = task.get("item")
        if isinstance(item, dict):
            item = item.get("id")
        if kind == "item" and isinstance(item, str):
            tasks += ["i:" + item, "q:" + item]
        elif kind == "fluid" and isinstance(task.get("fluid"), str):
            tasks.append("f:" + task["fluid"])
        elif kind == "dimension" and isinstance(task.get("dimension"), str):
            tasks.append("dim:" + task["dimension"])
    for reward in quest.get("rewards", []):
        item = reward.get("item")
        if isinstance(item, dict):
            item = item.get("id")
        if reward.get("type", "item") == "item" and isinstance(item, str):
            rewards += ["i:" + item, "q:" + item]
    return tasks, rewards


def check(quests_by_id: dict[str, dict], names: dict[str, str], stop_at: str | None = None):
    """Yield (quest id, message) for every task the player cannot do there and every reward from later on.

    With `stop_at`, yield (quest id, State) once: what the player has right before that quest.
    """
    model = Model()
    # a dimension task opens that dimension's ores and fluids
    for entry_dim in {d for e in model.worldgen for d in e["dimensions"]} - set(model.world_dimensions):
        model.rule([("dim:" + entry_dim,)], model.world_seed([entry_dim]), "dimension " + entry_dim)
    for qid, quest in quests_by_id.items():
        for token in quest_content(quest)[0] + quest_content(quest)[1]:
            model.t(token)
    model.compile()
    base = State(model)
    base.add(model.world_seed(model.world_dimensions))

    order, seen = [], set()

    def visit(qid):
        if qid in seen:
            return
        seen.add(qid)
        for dep in quests_by_id[qid].get("dependencies", []):
            if dep in quests_by_id:
                visit(dep)
        order.append(qid)

    for qid in quests_by_id:
        visit(qid)
    children: dict[str, int] = {q: 0 for q in quests_by_id}
    for q in quests_by_id.values():
        for dep in q.get("dependencies", []):
            if dep in children:
                children[dep] += 1
    after: dict[str, State] = {}
    descendants_tasks: dict[str, set[str]] = {}
    task_tokens = {qid: quest_content(q)[0] for qid, q in quests_by_id.items()}
    for qid in reversed(order):
        out = set()
        for other, q in quests_by_id.items():
            if qid in q.get("dependencies", []):
                out |= set(task_tokens[other]) | descendants_tasks.get(other, set())
        descendants_tasks[qid] = out

    for qid in order:
        quest = quests_by_id[qid]
        deps = [d for d in quest.get("dependencies", []) if d in after]
        one_of = quest.get("dependency_requirement", "all_completed") in ("one_completed", "one_started")
        if not deps:
            state = State(model, base)
        elif one_of and len(deps) > 1:
            shared = set.intersection(*(after[d].tokens() for d in deps))
            state = State(model, base)
            state.add_tokens(sorted(shared))
        else:
            state = State(model, after[deps[0]])
            for d in deps[1:]:
                state.union(after[d])
        tasks, rewards = quest_content(quest)
        if qid == stop_at:
            yield qid, state
            return
        for token in tasks:
            if token.startswith(("i:", "f:")) and not state.has(token):
                yield qid, f"asks for {token[2:]}, which the player cannot make at this point"
        state.add(tasks)
        for token in rewards:
            if token.startswith("q:"):
                if token[2:] in model.machine_items and token[2:] not in quest.get("_allow_machine_reward", []):
                    yield qid, (f"gives the machine {token[2:]}; the player should build it (give a reason with "
                                "allow_machine_reward if this is deliberate)")
                continue
            if not state.has(token):
                yield qid, f"gives {token[2:]}, which the player cannot make yet even after this quest"
            if token in descendants_tasks[qid]:
                yield qid, f"gives {token[2:]}, which a later quest asks the player to make"
        state.add(rewards)
        after[qid] = state
        for dep in deps:
            children[dep] -= 1
            if children[dep] == 0:
                del after[dep]  # nobody else needs it; keeps memory flat
    if model.unknown_generators:
        yield "", ("note: assumed LV output for multiblock generators missing from reachability.toml: "
                   + ", ".join(sorted(model.unknown_generators)))


def explain(state: State, name: str, depth: int = 3, indent: str = "", seen: set[str] | None = None) -> list[str]:
    """Why `name` is not reachable: the rules that make it and, for each, the slots still missing."""
    seen = seen if seen is not None else set()
    m = state.m
    if name in seen or name not in m.tok:
        return [] if name in seen else [indent + f"{name}: nothing makes it"]
    seen.add(name)
    if state.has(name):
        return [indent + f"{name}: reachable"]
    token = m.tok[name]
    makers = [r for r, (_s, outputs, _l) in enumerate(m.rules) if token in outputs]
    if not makers:
        return [indent + f"{name}: no recipe or world source"]
    lines = [indent + f"{name}: {len(makers)} way(s), none possible yet"]
    for r in sorted(makers, key=lambda r: state.missing[r])[:3]:
        slots, _outputs, label = m.rules[r]
        offset = m.offset[r]
        missing = [slot for s, slot in enumerate(slots) if not state.sat[offset + s]]
        lines.append(indent + f"  via {label}: missing " + "; ".join(
            " or ".join(m.names[t] for t in slot[:3]) + (" ..." if len(slot) > 3 else "") for slot in missing))
        if depth > 1:
            for slot in missing[:2]:
                lines.extend(explain(state, m.names[slot[0]], depth - 1, indent + "    ", seen))
    return lines


def derivation(state: State, name: str, stop: State | None = None, depth: int = 0, seen: set | None = None,
               limit: int = 6) -> list[str]:
    """How `state` first reached `name`: the rule, then (indented) how its inputs were reached. Tokens already
    present in `stop` are not expanded."""
    seen = seen if seen is not None else set()
    m = state.m
    token = m.tok.get(name)
    if token is None or name in seen or depth > limit or (stop is not None and stop.has(name)):
        return []
    seen.add(name)
    r = state.why.get(token)
    if r is None:
        return ["  " * depth + f"{name}: given (world, quest or seed)"]
    slots, _outputs, label = m.rules[r]
    used = []
    for slot in slots:
        options = [t for t in slot if state.have[t]]
        # the input reached first is the one that let the rule fire
        used.append(min(options, key=lambda t: list(state.why).index(t) if t in state.why else -1))
    lines = ["  " * depth + f"{name} <= [{label}] " + ", ".join(m.names[t] for t in used)]
    for t in used:
        lines.extend(derivation(state, m.names[t], stop, depth + 1, seen, limit))
    return lines


def unbooked_surface(state: State) -> tuple[State, dict[str, int]]:
    """What the player reaches if, at this point, they also build every machine they *could* build, including the
    ones the book never asks for. Returns the widened state and, per machine, how many tokens it opened.
    The difference with `state` is the room for shortcuts at this point of the book."""
    m = state.m
    machines = sorted(m.machine_items)
    full = State(m, state)
    opened: dict[str, int] = {}
    tried: set[str] = set()
    while True:
        new = [x for x in machines if x not in tried and full.has("i:" + x)]
        if not new:
            return full, opened
        tried.update(new)
        for machine in new:
            before = full.have.count(1)
            full.add(["q:" + machine])
            if full.have.count(1) > before:
                opened[machine] = full.have.count(1) - before
