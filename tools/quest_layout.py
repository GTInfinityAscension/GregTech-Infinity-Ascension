"""Layered layout for quest chapters, in the way the GTNH and GTO books read: the chapter runs left to right, each
column is one step of dependencies, quests in a column are ordered so lines cross as little as possible, and a line
that would still run across the chapter is hidden (FTB Quests can only hide all lines into a quest, or all lines out
of one, so the choice is made per quest).

Used by questgen.py for chapters with ``layout = "layered"`` in book.toml. Dependencies are never changed here: the
reachability check needs all of them; only positions and line visibility are.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field

X_STEP = 2.5      # distance between two columns of the skeleton
GAP = 1.0         # free space between two quests of the same column (satellites go there)
GRID = 0.5        # positions snap to this grid
LONG = 2          # a line spanning more columns than this is "long"
MAX_LINE = 5.0    # so is a line longer than this
SWEEPS = 24
HUB = 7           # a quest with this many dependents in the chapter is a hub
GALLERY = 5       # an anchor with more satellites than this gets them in a grid block


@dataclass
class Node:
    id: str
    size: float
    deps: list[str] = field(default_factory=list)
    kids: list[str] = field(default_factory=list)
    layer: int = 0
    order: float = 0.0
    y: float = 0.0
    dummy: bool = False


def _f(value) -> float:
    return float(str(value).rstrip("dD"))


def _true(value) -> bool:
    return str(value).lower() == "true"


def layout(chapter: dict, entry: str, exit_: str | None) -> dict:
    """Positions every quest of ``chapter`` (an FTB chapter dict) and sets its line flags. Returns metrics."""
    quests = {q["id"]: q for q in chapter["quests"]}
    deps = {i: [d for d in q.get("dependencies", []) if d in quests and d != i] for i, q in quests.items()}
    kids: dict[str, list[str]] = {i: [] for i in quests}
    for i, ds in deps.items():
        for d in ds:
            kids[d].append(i)
    # The skeleton is every quest that unlocks another one in the chapter; the rest are satellites placed in a ring
    # around the quest they hang from, as GTNH draws a hub and the machines it opens.
    core = dict.fromkeys(i for i in quests if kids[i] or i in (entry, exit_))  # ordered: a set's order changes per run
    # A hub that half the chapter needs (the LV motor, the tier's power) says nothing about where a quest belongs:
    # its lines are hidden and only the more specific prerequisites place a quest, unless it has no other one.
    hubs = {i for i in quests if len(kids[i]) >= HUB and i != entry}
    placing = {i: [d for d in deps[i] if d not in hubs] or deps[i] for i in quests}
    nodes = {i: Node(i, _f(quests[i].get("size", 1.0))) for i in core}
    for i in core:
        for d in placing[i]:
            if d in core:
                nodes[i].deps.append(d)
                nodes[d].kids.append(i)

    _assign_layers(nodes, entry, exit_)
    layers = _add_dummies(nodes)
    _order(layers, nodes)
    _place(layers, nodes)

    placed: list[tuple[float, float, float]] = []
    for i in core:
        q = quests[i]
        q["x"] = _snap(nodes[i].layer * X_STEP)
        q["y"] = _snap(nodes[i].y)
        placed.append((q["x"], q["y"], _f(q.get("size", 1.0)) / 2))
    level = {i: nodes[i].layer for i in core}
    satellites = [i for i in quests if i not in core]
    anchor = {}
    for i in satellites:
        ds = [d for d in placing[i] if d in core]
        anchor[i] = max(ds, key=lambda d: (level[d], len(kids[d]))) if ds else entry
    by_anchor: dict[str, list[str]] = {}
    for i in satellites:
        by_anchor.setdefault(anchor[i], []).append(i)
    segments = [((quests[d]["x"], quests[d]["y"]), (quests[i]["x"], quests[i]["y"]))
                for i in core for d in deps[i] if d in core]
    gallery: set[str] = set()
    for a in sorted(by_anchor, key=lambda a: (level[a], quests[a]["y"])):
        members = sorted(by_anchor[a], key=lambda i: (-_f(quests[i].get("size", 1.0)), str(quests[i].get("title"))))
        spots = []
        for i in members:
            others = [(quests[d]["x"], quests[d]["y"]) for d in deps[i] if d != a and d in core]
            spot = _ring_spot(quests[a], _f(quests[i].get("size", 1.0)) / 2, placed, others)
            spots.append(spot)
            placed.append((*spot, _f(quests[i].get("size", 1.0)) / 2))
        for i, (x, y) in zip(members, spots):
            quests[i]["x"], quests[i]["y"] = x, y
    _resolve_overlaps(quests, [i for i in quests if i not in core])
    for q in quests.values():
        q.pop("hide_dependency_lines", None)
        q.pop("hide_dependent_lines", None)
    # D-292: every line stays visible, as in the GTNH and GTO books; a quest without lines reads as lost. Only a
    # line that would run over another quest is hidden, as a last resort.
    _repair_lines_over_quests(quests, fixed={entry, exit_})
    _hide_lines_over_quests(quests)
    return measure(chapter)


# Ring around an anchor: right side first (the chapter reads left to right), then above and below, left last.
_ANGLES = [0, -45, 45, -90, 90, -135, 135, 180]


def _ring_spot(anchor: dict, radius: float, placed: list[tuple[float, float, float]],
               others: list[tuple[float, float]] | None = None) -> tuple[float, float]:
    """The first ring around the anchor with room; within it, the spot closest to the quest's other prerequisites."""
    ax, ay, ar = _f(anchor["x"]), _f(anchor["y"]), _f(anchor.get("size", 1.0)) / 2
    for ring in range(1, 8):
        free = []
        dist = ar + radius + 0.75 + (ring - 1) * 1.5
        steps = 8 * ring
        angles = _ANGLES if ring == 1 else sorted((k * 360 / steps for k in range(steps)),
                                                  key=lambda a: (abs(((a + 180) % 360) - 180), a))
        for angle in angles:
            x = _snap(ax + dist * math.cos(math.radians(angle)))
            y = _snap(ay + dist * math.sin(math.radians(angle)))
            # Square boxes, as the overlap check and the quest icons are: Chebyshev distance, not Euclidean.
            if all(max(abs(x - px), abs(y - py)) >= pr + radius + 0.25 for px, py, pr in placed) and \
                    _clear((ax, ay), (x, y), placed, ar, radius):
                if not others:
                    return x, y
                free.append((sum(math.dist((x, y), o) for o in others), x, y))
        if free:
            _, x, y = min(free)
            return x, y
    return _snap(ax + 2), _snap(ay + 2 * len(placed) % 7)


def _gallery_spots(anchor: dict, members: list[str], quests: dict[str, dict], placed: list, segments: list):
    """A compact grid block next to its anchor, clear of other quests and of the skeleton's lines."""
    size = max(_f(quests[i].get("size", 1.0)) for i in members)
    step = size + 0.5
    cols = min(5, math.ceil(math.sqrt(len(members))))
    rows = math.ceil(len(members) / cols)
    ax, ay, ar = _f(anchor["x"]), _f(anchor["y"]), _f(anchor.get("size", 1.0)) / 2
    best = None
    for dist in range(0, 40):
        for dx, dy in ((1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1), (-1, 0)):
            ox = ax + dx * (ar + 0.75 + dist * 0.5) + (0 if dx >= 0 else -(cols - 1) * step)
            oy = ay + dy * (ar + 0.75 + dist * 0.5) + (-(rows - 1) * step / 2 if dy == 0 else
                                                       (0 if dy > 0 else -(rows - 1) * step))
            cells = [(_snap(ox + (k % cols) * step), _snap(oy + (k // cols) * step)) for k in range(len(members))]
            if all(max(abs(x - px), abs(y - py)) >= pr + size / 2 + 0.25 for x, y in cells for px, py, pr in placed) \
                    and not any(_near_segment((x, y), s, size / 2 + 0.3) for x, y in cells for s in segments):
                best = cells
                break
        if best:
            break
    best = best or [(_snap(ax + 3 + (k % cols) * step), _snap(ay + 30 + (k // cols) * step))
                    for k in range(len(members))]
    for (x, y), i in zip(best, members):
        placed.append((x, y, _f(quests[i].get("size", 1.0)) / 2))
    return best


def _resolve_overlaps(quests: dict[str, dict], movable: list[str]) -> None:
    """Last guard: a satellite whose box still touches another quest moves down until it is free."""
    def touches(i: str) -> bool:
        a = quests[i]
        return any(max(abs(_f(a["x"]) - _f(b["x"])), abs(_f(a["y"]) - _f(b["y"]))) <
                   (_f(a.get("size", 1.0)) + _f(b.get("size", 1.0))) / 2 + 0.1 for j, b in quests.items() if j != i)

    for i in movable:
        while touches(i):
            quests[i]["y"] = _snap(_f(quests[i]["y"]) + GRID)


def _near_segment(p, seg, radius) -> bool:
    (ax, ay), (bx, by) = seg
    length = (bx - ax) ** 2 + (by - ay) ** 2
    u = max(0.0, min(1.0, ((p[0] - ax) * (bx - ax) + (p[1] - ay) * (by - ay)) / length)) if length else 0.0
    return math.dist((ax + u * (bx - ax), ay + u * (by - ay)), p) < radius


def _clear(a, b, placed, ra, rb) -> bool:
    """The straight line a-b does not run over another quest."""
    for px, py, pr in placed:
        if math.dist(a, (px, py)) < ra + 0.01 or math.dist(b, (px, py)) < rb + 0.01:
            continue
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((px - a[0]) * dx + (py - a[1]) * dy) / length)) if length else 0.0
        if math.dist((a[0] + t * dx, a[1] + t * dy), (px, py)) < pr + 0.15:
            return False
    return True


def _snap(v: float) -> float:
    return round(v / GRID) * GRID


def _assign_layers(nodes: dict[str, Node], entry: str, exit_: str | None) -> None:
    order = _topological(nodes)
    for i in order:
        n = nodes[i]
        n.layer = 0 if i == entry else 1 + max((nodes[d].layer for d in n.deps), default=0)
    # Pull each quest right towards the quests that need it, when that shortens its lines: a part used only by late
    # machines sits next to them, not at the start of the chapter.
    for _ in range(4):
        for i in reversed(order):
            n = nodes[i]
            if i in (entry, exit_) or not n.kids:
                continue
            low = 1 + max((nodes[d].layer for d in n.deps), default=0)
            high = min(nodes[k].layer for k in n.kids) - 1
            if high <= low:
                n.layer = low
                continue
            spans = [nodes[d].layer for d in n.deps] + [nodes[k].layer for k in n.kids]
            best = min(range(low, high + 1), key=lambda l: (sum(abs(l - s) for s in spans), -l))
            n.layer = best
    if exit_ in nodes:
        nodes[exit_].layer = max(n.layer for n in nodes.values() if n.id != exit_) + 1
    # Optional leaves (hints, extras) stay right next to the quest they hang from.
    for n in nodes.values():
        if not n.kids and n.deps and n.id != exit_:
            n.layer = max(nodes[d].layer for d in n.deps) + 1


def _topological(nodes: dict[str, Node]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    def visit(i: str, trail: set[str]) -> None:
        if i in seen or i in trail:
            return
        trail.add(i)
        for d in nodes[i].deps:
            visit(d, trail)
        trail.discard(i)
        seen.add(i)
        out.append(i)

    for i in sorted(nodes):
        visit(i, set())
    return out


def _add_dummies(nodes: dict[str, Node]) -> list[list[str]]:
    """Long edges get one virtual node per column they pass, so the ordering keeps their path clear."""
    for n in list(nodes.values()):
        if n.dummy:
            continue
        for dep in list(n.deps):
            span = n.layer - nodes[dep].layer
            if span <= 1 or span > LONG:
                continue
            prev = dep
            for layer in range(nodes[dep].layer + 1, n.layer):
                v = Node(f"~{dep}>{n.id}@{layer}", 0.25, [prev], [], layer, dummy=True)
                nodes[v.id] = v
                nodes[prev].kids.append(v.id)
                prev = v.id
            nodes[prev].kids.append(n.id)
            n.deps.append(prev)
    count = max(n.layer for n in nodes.values()) + 1
    layers: list[list[str]] = [[] for _ in range(count)]
    for n in nodes.values():
        layers[n.layer].append(n.id)
    return layers


def _neighbours(n: Node, nodes: dict[str, Node], layer: int) -> list[str]:
    return [d for d in n.deps if nodes[d].layer == layer] + [k for k in n.kids if nodes[k].layer == layer]


def _order(layers: list[list[str]], nodes: dict[str, Node]) -> None:
    # Start from a depth-first order so families stay together.
    rank: dict[str, int] = {}
    counter = itertools.count()

    def dfs(i: str) -> None:
        if i in rank:
            return
        rank[i] = next(counter)
        for k in sorted(nodes[i].kids, key=lambda k: nodes[k].layer):
            dfs(k)

    for layer in layers:
        for i in sorted(layer):
            dfs(i)
    for layer in layers:
        layer.sort(key=lambda i: rank[i])
        for pos, i in enumerate(layer):
            nodes[i].order = pos

    best = [list(l) for l in layers]
    best_cross = _crossings(layers, nodes)
    for sweep in range(SWEEPS):
        down = sweep % 2 == 0
        rng = range(1, len(layers)) if down else range(len(layers) - 2, -1, -1)
        for li in rng:
            ref = li - 1 if down else li + 1
            layer = layers[li]
            for i in layer:
                ns = _neighbours(nodes[i], nodes, ref)
                if ns:
                    vals = sorted(nodes[x].order for x in ns)
                    m = len(vals) // 2
                    nodes[i].y = vals[m] if len(vals) % 2 else (vals[m - 1] + vals[m]) / 2
                else:
                    nodes[i].y = nodes[i].order
            layer.sort(key=lambda i: (nodes[i].y, nodes[i].order))
            for pos, i in enumerate(layer):
                nodes[i].order = pos
        _transpose(layers, nodes)
        c = _crossings(layers, nodes)
        if c < best_cross:
            best_cross, best = c, [list(l) for l in layers]
    for li, layer in enumerate(best):
        layers[li] = layer
        for pos, i in enumerate(layer):
            nodes[i].order = pos


def _pair_crossings(a: str, b: str, layer: int, nodes: dict[str, Node]) -> int:
    c = 0
    for side in (layer - 1, layer + 1):
        na = [nodes[x].order for x in _neighbours(nodes[a], nodes, side)]
        nb = [nodes[x].order for x in _neighbours(nodes[b], nodes, side)]
        c += sum(1 for p in na for q in nb if p > q)
    return c


def _transpose(layers: list[list[str]], nodes: dict[str, Node]) -> None:
    improved = True
    rounds = 0
    while improved and rounds < 8:
        improved = False
        rounds += 1
        for li, layer in enumerate(layers):
            for j in range(len(layer) - 1):
                a, b = layer[j], layer[j + 1]
                if _pair_crossings(a, b, li, nodes) > _pair_crossings(b, a, li, nodes):
                    layer[j], layer[j + 1] = b, a
                    nodes[a].order, nodes[b].order = j + 1, j
                    improved = True


def _crossings(layers: list[list[str]], nodes: dict[str, Node]) -> int:
    total = 0
    for li in range(len(layers) - 1):
        edges = [(nodes[i].order, nodes[k].order) for i in layers[li] for k in nodes[i].kids
                 if nodes[k].layer == li + 1]
        for (a, b), (c, d) in itertools.combinations(edges, 2):
            if (a - c) * (b - d) < 0:
                total += 1
    return total


def _place(layers: list[list[str]], nodes: dict[str, Node]) -> None:
    """Vertical positions: each quest moves towards the average height of its neighbours, keeping its column order and
    the minimum spacing (a pool-adjacent-violators fit), so lines run as flat as the order allows."""
    for layer in layers:
        y = 0.0
        for i in layer:
            n = nodes[i]
            n.y = y + n.size / 2
            y += n.size + GAP
        shift = y / 2
        for i in layer:
            nodes[i].y -= shift
    for it in range(30):
        seq = range(len(layers)) if it % 2 == 0 else range(len(layers) - 1, -1, -1)
        for li in seq:
            layer = layers[li]
            want = []
            for i in layer:
                n = nodes[i]
                ns = [nodes[x].y for x in n.deps + n.kids if x in nodes]
                want.append(sum(ns) / len(ns) if ns else n.y)
            _fit(layer, want, nodes)


def _fit(layer: list[str], want: list[float], nodes: dict[str, Node]) -> None:
    # Offsets so that quest k may sit at want[k] - off[k] with all gaps respected; isotonic regression on the rest.
    offs, acc = [], 0.0
    for idx, i in enumerate(layer):
        if idx:
            prev = nodes[layer[idx - 1]]
            acc += (prev.size + nodes[i].size) / 2 + GAP
        offs.append(acc)
    vals = [w - o for w, o in zip(want, offs)]
    blocks: list[list[float]] = []  # [sum, count]
    for v in vals:
        blocks.append([v, 1])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
            s, c = blocks.pop()
            blocks[-1][0] += s
            blocks[-1][1] += c
    fitted = []
    for s, c in blocks:
        fitted += [s / c] * c
    for i, base, o in zip(layer, fitted, offs):
        nodes[i].y = base + o


def _hide_long_lines(quests: dict[str, dict], level: dict[str, int]) -> None:
    def long(dep: str, kid: str) -> bool:
        a, b = quests[dep], quests[kid]
        return level[kid] - level[dep] > LONG or math.dist((a["x"], a["y"]), (b["x"], b["y"])) > MAX_LINE

    deps_of = {i: [d for d in q.get("dependencies", []) if d in quests and d != i] for i, q in quests.items()}
    kids_of: dict[str, list[str]] = {i: [] for i in quests}
    for i, ds in deps_of.items():
        for d in ds:
            kids_of[d].append(i)
    # A hub whose lines mostly run far hides its outgoing lines (the quests that need it say so in their text).
    for i, ks in kids_of.items():
        far = [k for k in ks if long(i, k)]
        if len(ks) >= 4 and len(far) * 2 > len(ks):
            quests[i]["hide_dependent_lines"] = True
    for i, ds in deps_of.items():
        shown = [d for d in ds if not quests[d].get("hide_dependent_lines")]
        far = [d for d in shown if long(d, i)]
        if far and len(far) * 2 >= len(shown):
            quests[i]["hide_dependency_lines"] = True


def _visible_edges(quests: dict[str, dict]) -> list[tuple[str, str]]:
    edges = []
    for i, q in quests.items():
        if _true(q.get("hide_dependency_lines", False)):
            continue
        for dep in q.get("dependencies", []):
            if dep in quests and dep != i and not _true(quests[dep].get("hide_dependent_lines", False)):
                edges.append((dep, i))
    return edges


def _crossing_pairs(quests: dict[str, dict], edges: list[tuple[str, str]]) -> list[tuple[tuple, tuple]]:
    pos = {i: (_f(q["x"]), _f(q["y"])) for i, q in quests.items()}

    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    out = []
    for e, f in itertools.combinations(edges, 2):
        if len({*e, *f}) == 4:
            p, q, r, s = pos[e[0]], pos[e[1]], pos[f[0]], pos[f[1]]
            if orient(p, q, r) * orient(p, q, s) < 0 and orient(r, s, p) * orient(r, s, q) < 0:
                out.append((e, f))
    return out


def _runs_over(quests: dict[str, dict], dep: str, kid: str, margin: float = 0.1, scale: float = 0.5) -> bool:
    a, b = quests[dep], quests[kid]
    ax, ay, bx, by = _f(a["x"]), _f(a["y"]), _f(b["x"]), _f(b["y"])
    length = math.hypot(bx - ax, by - ay)
    if not length:
        return False
    for i, c in quests.items():
        if i in (dep, kid):
            continue
        cx, cy = _f(c["x"]), _f(c["y"])
        u = max(0.0, min(1.0, ((cx - ax) * (bx - ax) + (cy - ay) * (by - ay)) / length ** 2))
        if math.hypot(ax + u * (bx - ax) - cx, ay + u * (by - ay) - cy) < _f(c.get("size", 1.0)) * scale + margin:
            return True
    return False


def _blocked(quests: dict[str, dict], i: str) -> bool:
    """A line of quest i runs over another quest, or a drawn line runs over quest i."""
    q = quests[i]
    mine = [(d, i) for d in q.get("dependencies", []) if d in quests and d != i]
    mine += [(i, k) for k, b in quests.items() if i in b.get("dependencies", [])]
    return any(_runs_over(quests, d, k) for d, k in mine) or \
        any(i not in (d, k) and _over_one(quests, d, k, i) for d, k in _visible_edges(quests))


def _blockers(quests: dict[str, dict]) -> list[tuple[str, str, str]]:
    """(dep, kid, quest under the line) for every visible line that runs over another quest."""
    out = []
    for dep, kid in _visible_edges(quests):
        a, b = quests[dep], quests[kid]
        ax, ay, bx, by = _f(a["x"]), _f(a["y"]), _f(b["x"]), _f(b["y"])
        length = math.hypot(bx - ax, by - ay)
        if not length:
            continue
        for i, c in quests.items():
            if i in (dep, kid):
                continue
            cx, cy = _f(c["x"]), _f(c["y"])
            u = max(0.0, min(1.0, ((cx - ax) * (bx - ax) + (cy - ay) * (by - ay)) / length ** 2))
            if math.hypot(ax + u * (bx - ax) - cx, ay + u * (by - ay) - cy) < _f(c.get("size", 1.0)) * 0.5 + 0.1:
                out.append((dep, kid, i))
    return out


def _repair_lines_over_quests(quests: dict[str, dict], fixed: set) -> None:
    """Moves the quest under a line, or the line's own quest, to the nearest free spot where no line runs over it and
    none of its own lines runs over another quest. Only the lines touching the moved quest are recounted."""
    edges = _visible_edges(quests)
    touching: dict[str, list[tuple[str, str]]] = {i: [] for i in quests}
    for dep, kid in edges:
        touching[dep].append((dep, kid))
        touching[kid].append((dep, kid))

    def over(dep: str, kid: str, c: str) -> bool:
        a, b, q = quests[dep], quests[kid], quests[c]
        ax, ay, bx, by, cx, cy = _f(a["x"]), _f(a["y"]), _f(b["x"]), _f(b["y"]), _f(q["x"]), _f(q["y"])
        length = (bx - ax) ** 2 + (by - ay) ** 2
        if not length:
            return False
        u = max(0.0, min(1.0, ((cx - ax) * (bx - ax) + (cy - ay) * (by - ay)) / length))
        return math.hypot(ax + u * (bx - ax) - cx, ay + u * (by - ay) - cy) < _f(q.get("size", 1.0)) * 0.5 + 0.1

    def cost(m: str) -> int:
        n = sum(1 for d, k in edges if m not in (d, k) and over(d, k, m))
        return n + sum(1 for d, k in touching[m] for c in quests if c not in (d, k) and over(d, k, c))

    def overlaps(i: str) -> bool:
        a = quests[i]
        return any(max(abs(_f(a["x"]) - _f(b["x"])), abs(_f(a["y"]) - _f(b["y"]))) <
                   (_f(a.get("size", 1.0)) + _f(b.get("size", 1.0))) / 2 + 0.25 for j, b in quests.items() if j != i)

    offsets = sorted({(dx * 0.5, dy * 0.5) for dx in range(-6, 7) for dy in range(-6, 7)} - {(0, 0)},
                     key=lambda o: (abs(o[0]) + abs(o[1]), o))
    for _ in range(4):
        conflicts = _blockers(quests)
        if not conflicts:
            return
        for dep, kid, blocker in conflicts:
            if not over(dep, kid, blocker):
                continue  # an earlier move already fixed it
            for mover in (blocker, kid):
                if mover in fixed:
                    continue
                q = quests[mover]
                ox, oy = q["x"], q["y"]
                for dx, dy in offsets:
                    q["x"], q["y"] = ox + dx, oy + dy
                    if not overlaps(mover) and cost(mover) == 0:
                        break
                else:
                    q["x"], q["y"] = ox, oy
                    continue
                break


def _relocate_blocked(quests: dict[str, dict], fixed: set, reach: float = 6.0) -> None:
    """For each movable quest whose lines run over a quest (or that a line runs over), the nearest free spot around
    one of its dependencies, then around its old place, where none of its lines runs over a quest and no line runs
    over it. Quests on a fixed spot only get their blockers moved."""
    def clear(i: str) -> bool:
        q = quests[i]
        for j, b in quests.items():
            if j != i and max(abs(_f(q["x"]) - _f(b["x"])), abs(_f(q["y"]) - _f(b["y"]))) < \
                    (_f(q.get("size", 1.0)) + _f(b.get("size", 1.0))) / 2 + 0.25:
                return False
        mine = [(d, i) for d in q.get("dependencies", []) if d in quests and d != i]
        mine += [(i, k) for k, b in quests.items() if i in b.get("dependencies", [])]
        if any(_runs_over(quests, d, k) for d, k in mine):
            return False
        return not any(i not in (d, k) and _over_one(quests, d, k, i) for d, k in _visible_edges(quests))

    steps = int(reach * 2)
    ring = sorted({(dx * 0.5, dy * 0.5) for dx in range(-steps, steps + 1) for dy in range(-steps, steps + 1)},
                  key=lambda o: math.hypot(*o))
    for _ in range(3):
        bad = {k for d, k in _visible_edges(quests) if _runs_over(quests, d, k)}
        bad |= {b for _d, _k, b in _blockers(quests)}
        if not bad:
            return
        for i in sorted(bad):
            if i in fixed or clear(i):
                continue
            q = quests[i]
            ox, oy = q["x"], q["y"]
            anchors = [(_f(quests[d]["x"]), _f(quests[d]["y"])) for d in q.get("dependencies", []) if d in quests]
            for ax, ay in anchors + [(ox, oy)]:
                for dx, dy in ring:
                    if math.hypot(dx, dy) < 1.5 and (ax, ay) != (ox, oy):
                        continue
                    q["x"], q["y"] = ax + dx, ay + dy
                    if clear(i):
                        break
                else:
                    continue
                break
            else:
                q["x"], q["y"] = ox, oy


def _over_one(quests: dict[str, dict], dep: str, kid: str, c: str) -> bool:
    a, b, q = quests[dep], quests[kid], quests[c]
    ax, ay, bx, by, cx, cy = _f(a["x"]), _f(a["y"]), _f(b["x"]), _f(b["y"]), _f(q["x"]), _f(q["y"])
    length = (bx - ax) ** 2 + (by - ay) ** 2
    if not length:
        return False
    u = max(0.0, min(1.0, ((cx - ax) * (bx - ax) + (cy - ay) * (by - ay)) / length))
    return math.hypot(ax + u * (bx - ax) - cx, ay + u * (by - ay) - cy) < _f(q.get("size", 1.0)) * 0.5 + 0.1


def _hide_lines_over_quests(quests: dict[str, dict]) -> None:
    for dep, kid in _visible_edges(quests):
        if _runs_over(quests, dep, kid):
            quests[kid]["hide_dependency_lines"] = True


def _prune_crossings(quests: dict[str, dict]) -> None:
    """Hide the lines into a quest when one of them runs over another quest; then, while some quest's incoming lines
    take part in at least two crossings per line, hide that quest's lines."""
    for dep, kid in _visible_edges(quests):
        if _runs_over(quests, dep, kid):
            quests[kid]["hide_dependency_lines"] = True
    while True:
        edges = _visible_edges(quests)
        pairs = _crossing_pairs(quests, edges)
        if not pairs:
            return
        score: dict[str, int] = {}
        for e, f in pairs:
            for kid in {e[1], f[1]}:
                score[kid] = score.get(kid, 0) + 1
        lines = {}
        for _, kid in edges:
            lines[kid] = lines.get(kid, 0) + 1
        best = max(score, key=lambda k: (score[k] / lines[k], score[k]))
        if score[best] < 2 * lines[best]:
            return
        quests[best]["hide_dependency_lines"] = True


def measure(chapter: dict) -> dict:
    quests = {q["id"]: q for q in chapter["quests"]}
    pos = {i: (_f(q["x"]), _f(q["y"])) for i, q in quests.items()}
    edges = []
    for i, q in quests.items():
        if _true(q.get("hide_dependency_lines", False)):
            continue
        for dep in q.get("dependencies", []):
            if dep in quests and not _true(quests[dep].get("hide_dependent_lines", False)):
                edges.append((dep, i))

    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    crossings = 0
    for (a, b), (c, d) in itertools.combinations(edges, 2):
        if len({a, b, c, d}) == 4:
            p, q, r, s = pos[a], pos[b], pos[c], pos[d]
            if orient(p, q, r) * orient(p, q, s) < 0 and orient(r, s, p) * orient(r, s, q) < 0:
                crossings += 1
    long_lines = sum(1 for a, b in edges if math.dist(pos[a], pos[b]) > 5)
    deps = sum(1 for q in quests.values() for d in q.get("dependencies", []) if d in quests)
    xs = [p[0] for p in pos.values()] or [0]
    ys = [p[1] for p in pos.values()] or [0]
    return {"quests": len(quests), "deps": deps, "visible": len(edges), "crossings": crossings, "long": long_lines,
            "width": max(xs) - min(xs), "height": max(ys) - min(ys)}
