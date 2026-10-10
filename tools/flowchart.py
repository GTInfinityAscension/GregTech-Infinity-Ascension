#!/usr/bin/env python3
"""Processing-line flowcharts for the quest book: quests-src/flowcharts/<name>.toml -> Graphviz -> PNG.

    flowchart.py                  render every chart into modpack/docs/flowcharts/ (recipe control)
    flowchart.py quests <chapter|file.toml>   quest tree of a chapter or a draft, as PNG and as a draw.io file
                                  (design before FTB Quests)

Style of GregTech flowcharts: green hexagon = machine, box = material, pink circle = residue, coloured area =
sub-line. The charts are a design and control tool for processing lines; they are not shown in the quest book.
Needs Graphviz (`dot`).
"""
import subprocess, sys, tomllib
from pathlib import Path

BG, EDGE, TEXT = "#181818", "#e8e8e8", "#ffffff"
MACHINE = dict(shape="hexagon", style="filled", fillcolor="#4b8a1c", color="#5fa82a", fontcolor="#0d0d0d",
               fontsize="17", fontname="Helvetica", width="2.3", height="1.05", fixedsize="true")
MATERIAL = dict(shape="box", style="filled", fillcolor="#0d0d0d", color="#f0f0f0", fontcolor=TEXT,
                fontsize="12", fontname="Helvetica", margin="0.12,0.06")
RESIDUE = dict(shape="circle", style="filled", fillcolor="#f08080", color="#f08080", fontcolor="#1a1a1a",
               fontsize="11", fontname="Helvetica", width="0.8", fixedsize="true")
AREAS = {"green": ("#0d2e0a", "#4b8a1c"), "teal": ("#06302a", "#3aa58a"), "brown": ("#2e2405", "#b08a2a")}

def attrs(d): return ", ".join(f'{k}="{v}"' for k, v in d.items())

def render(spec: dict, out: Path) -> None:
    lines = [f'digraph G {{ graph [bgcolor="{BG}", rankdir={spec.get("direction","LR")}, nodesep=0.35, ranksep=0.55, '
             f'fontcolor="{TEXT}", fontname="Helvetica", pad=0.4, labelloc=t, fontsize=22, label="{spec["title"]}"];',
             f'edge [color="{EDGE}", arrowsize=0.7, penwidth=1.3, fontcolor="#cfcfcf", fontsize=11, fontname="Helvetica"];']
    def node(n, kind, label, extra=None):
        style = {"machine": MACHINE, "material": MATERIAL, "residue": RESIDUE}[kind]
        sub = f'<BR/><FONT POINT-SIZE="11">{extra}</FONT>' if extra else ""
        return f'"{n}" [{attrs(style)}, label=<{label}{sub}>];'
    declared = set()
    def emit(items, indent=""):
        for m in items:
            declared.add(m["id"])
            lines.append(indent + node(m["id"], m["kind"], m["label"], m.get("note")))
    emit([n for n in spec["node"] if "area" not in n])
    for i, area in enumerate(spec.get("area", [])):
        fill, border = AREAS[area.get("colour", "green")]
        lines.append(f'subgraph cluster_{i} {{ label="{area["label"]}"; labeljust=l; labelloc=b; style=filled; '
                     f'fillcolor="{fill}"; color="{border}"; fontcolor="{TEXT}"; fontsize=13;')
        emit([n for n in spec["node"] if n.get("area") == area["id"]], "  ")
        lines.append("}")
    for e in spec["edge"]:
        label = f' [label="{e[2]}"]' if len(e) > 2 else ""
        lines.append(f'"{e[0]}" -> "{e[1]}"{label};')
    lines.append("}")
    dot = out.with_suffix(".dot"); dot.write_text("\n".join(lines))
    subprocess.run(["dot", "-Tpng", "-Gdpi=90", str(dot), "-o", str(out)], check=True)

PACK = Path(__file__).resolve().parents[1]
SRC = PACK / "quests-src" / "flowcharts"
OUT = PACK / "docs" / "flowcharts"

ROLE_STYLE = {
    "milestone": dict(shape="doubleoctagon", style="filled", fillcolor="#c9a227", color="#e8c547", fontcolor="#111111"),
    "spine": dict(shape="hexagon", style="filled", fillcolor="#4b8a1c", color="#5fa82a", fontcolor="#0d0d0d"),
    "gate": dict(shape="hexagon", style="filled", fillcolor="#b5651d", color="#d98a3a", fontcolor="#0d0d0d"),
    "side": dict(shape="box", style="filled", fillcolor="#0d0d0d", color="#f0f0f0", fontcolor=TEXT),
    "detail": dict(shape="box", style="filled", fillcolor="#0d0d0d", color="#8a8a8a", fontcolor="#cfcfcf"),
}
OPTIONAL = dict(shape="box", style="dashed", color="#7a7a7a", fontcolor="#9a9a9a")
GROUPS = {  # group -> (label, fill, border)
    "wood": ("Wood chemistry", "#2e2405", "#b08a2a"), "lime": ("Lime", "#06302a", "#3aa58a"),
    "large": ("Steam components", "#1a1a2e", "#6a6ad8"), "ore": ("Large: ore line", "#0d2e0a", "#4b8a1c"),
    "forming": ("Large: metal forming", "#2e0d0d", "#c05050"), "heat": ("Large: heat and mixing", "#2e1a05", "#d98a3a"),
    "circuit": ("Track: the circuit", "#101e2e", "#4a90d9"), "hull": ("Track: the hull", "#23102e", "#9a5ad8"),
    "lvshop": ("Machine shop", "#1e1e1e", "#9a9a9a"), "mvshop": ("Machine shop", "#1e1e1e", "#9a9a9a"),
    "lvchem": ("Chlor-alkali and the first chemistry", "#06302a", "#3aa58a"), "bio": ("Plants to plastic", "#0d2e0a", "#4b8a1c"),
    "ebf": ("The Electric Blast Furnace", "#2e1a05", "#d98a3a"), "lvmulti": ("GTNA multiblocks", "#1a1a2e", "#6a6ad8"),
    "bayer": ("Bayer and Hall-Héroult", "#2e2405", "#b08a2a"), "acid": ("Contact, Haber-Bosch, Solvay", "#06302a", "#3aa58a"),
}
# draw.io look for each role
DRAWIO = {
    "milestone": "shape=hexagon;perimeter=hexagonPerimeter2;size=0.2;fillColor=#c9a227;strokeColor=#e8c547;strokeWidth=3;fontColor=#111111;fontStyle=1;",
    "spine": "shape=hexagon;perimeter=hexagonPerimeter2;size=0.2;fillColor=#4b8a1c;strokeColor=#5fa82a;fontColor=#0d0d0d;",
    "gate": "shape=hexagon;perimeter=hexagonPerimeter2;size=0.2;fillColor=#b5651d;strokeColor=#d98a3a;fontColor=#0d0d0d;",
    "side": "rounded=1;fillColor=#0d0d0d;strokeColor=#f0f0f0;fontColor=#ffffff;",
    "detail": "rounded=1;fillColor=#0d0d0d;strokeColor=#8a8a8a;fontColor=#cfcfcf;",
    "optional": "rounded=1;dashed=1;fillColor=none;strokeColor=#7a7a7a;fontColor=#9a9a9a;",
    "external": "shape=note;size=10;dashed=1;fillColor=none;strokeColor=#6aa0d8;fontColor=#6aa0d8;",
}


def quest_tree(path: Path) -> tuple[str, list[dict], dict[str, str], dict[str, str]]:
    """(chapter title, quests, node key -> role, node key -> label) for a quests-src chapter or draft."""
    spec = tomllib.loads(path.read_text(encoding="utf-8"))
    quests = spec.get("quest", [])
    roles, labels = {"entry": "milestone"}, {"entry": spec["chapter"]["title"]}
    for q in quests:
        roles[q["key"]] = q.get("role", "side") if q.get("role", "side") in ROLE_STYLE else "optional"
        task = ", ".join(t.get("item", "").split(":")[-1] for t in q.get("task", []) if "item" in t)
        labels[q["key"]] = q.get("title", q["key"]).replace('"', "'") + (f"\n{task}" if task else "")
    if "exit" in spec:
        quests = quests + [{"key": "exit", "deps": spec["exit"]["deps"]}]
        roles["exit"], labels["exit"] = "milestone", spec["exit"].get("title", "Exit")
    for q in quests:
        for dep in q.get("deps", []):
            if dep not in roles:
                roles[dep], labels[dep] = "external", dep
    return spec["chapter"]["title"], quests, roles, labels


def render_quests(path: Path, out: Path) -> None:
    """The dependency tree of one chapter, laid out automatically (PNG), plus the same tree as a draw.io file."""
    title, quests, roles, labels = quest_tree(path)
    groups = {q["key"]: q["group"] for q in quests if q.get("group") in GROUPS}
    def node(key):
        style = ROLE_STYLE.get(roles[key]) or (OPTIONAL if roles[key] == "optional" else
                                                dict(shape="note", style="dashed", color="#6aa0d8", fontcolor="#6aa0d8"))
        return f'"{key}" [{attrs(style)}, label="{labels[key]}"];'
    lines = [f'digraph Q {{ graph [bgcolor="{BG}", rankdir=LR, nodesep=0.25, ranksep=0.5, pad=0.4, fontcolor="{TEXT}",'
             f' fontname="Helvetica", labelloc=t, fontsize=22, label="Quest tree: {title}"];',
             'node [fontname="Helvetica", fontsize=11, margin="0.10,0.04"];',
             f'edge [color="{EDGE}", arrowsize=0.6];']
    for key in roles:
        if key not in groups:
            lines.append(node(key))
    for g, (label, fill, border) in GROUPS.items():
        members = [k for k, v in groups.items() if v == g]
        if members:
            lines.append(f'subgraph cluster_{g} {{ label="{label}"; style=filled; fillcolor="{fill}"; color="{border}"; '
                         f'fontcolor="{TEXT}"; fontsize=13; labeljust=l;')
            lines.extend("  " + node(k) for k in members)
            lines.append("}")
    edges = [(dep, q["key"]) for q in quests for dep in q.get("deps", [])]
    lines.extend(f'"{a}" -> "{b}";' for a, b in edges)
    lines.append("}")
    dot = "\n".join(lines)
    subprocess.run(["dot", "-Tpng", "-Gdpi=80", "-o", str(out)], input=dot.encode(), check=True)
    plain = subprocess.run(["dot", "-Tplain"], input=dot.encode(), check=True, capture_output=True).stdout.decode()
    write_drawio(out.with_suffix(".drawio"), title, plain, roles, labels, groups, edges)


def write_drawio(path: Path, title: str, plain: str, roles, labels, groups, edges) -> None:
    """A draw.io file with Graphviz's positions: open it in draw.io to read, move or annotate the tree."""
    from xml.sax.saxutils import escape
    scale = 72
    graph_h, pos = 0.0, {}
    for line in plain.splitlines():
        parts = line.split()
        if parts[0] == "graph":
            graph_h = float(parts[3])
        elif parts[0] == "node":
            key = parts[1].strip('"')
            x, y, w, h = map(float, parts[2:6])
            pos[key] = (x - w / 2, graph_h - y - h / 2, w, h)
    cells, ids = [], {}
    for g, (label, fill, border) in GROUPS.items():
        members = [pos[k] for k, v in groups.items() if v == g and k in pos]
        if not members:
            continue
        x0 = min(m[0] for m in members) - 0.2
        y0 = min(m[1] for m in members) - 0.35
        x1 = max(m[0] + m[2] for m in members) + 0.2
        y1 = max(m[1] + m[3] for m in members) + 0.2
        cells.append(f'<mxCell id="grp_{g}" value="{escape(label)}" style="rounded=1;fillColor={fill};strokeColor={border};'
                     f'fontColor=#ffffff;verticalAlign=top;align=left;spacingLeft=6;container=0;" vertex="1" parent="1">'
                     f'<mxGeometry x="{x0 * scale:.0f}" y="{y0 * scale:.0f}" width="{(x1 - x0) * scale:.0f}" '
                     f'height="{(y1 - y0) * scale:.0f}" as="geometry"/></mxCell>')
    for n, (key, (x, y, w, h)) in enumerate(pos.items()):
        ids[key] = f"n{n}"
        style = DRAWIO.get(roles.get(key, "side"), DRAWIO["side"]) + "whiteSpace=wrap;html=1;fontSize=11;"
        value = escape(labels.get(key, key).replace("\\n", "\n")).replace("\n", "&lt;br&gt;")
        cells.append(f'<mxCell id="n{n}" value="{value}" style="{style}" vertex="1" parent="1">'
                     f'<mxGeometry x="{x * scale:.0f}" y="{y * scale:.0f}" width="{w * scale:.0f}" height="{h * scale:.0f}" '
                     f'as="geometry"/></mxCell>')
    for n, (a, b) in enumerate(edges):
        if a in ids and b in ids:
            cells.append(f'<mxCell id="e{n}" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#e8e8e8;'
                         f'endArrow=block;endSize=4;" edge="1" parent="1" source="{ids[a]}" target="{ids[b]}">'
                         f'<mxGeometry relative="1" as="geometry"/></mxCell>')
    xml = (f'<mxfile host="gtia-flowchart"><diagram name="{escape(title)}"><mxGraphModel background="#181818" grid="0">'
           f'<root><mxCell id="0"/><mxCell id="1" parent="0"/>{"".join(cells)}</root></mxGraphModel></diagram></mxfile>')
    path.write_text(xml, encoding="utf-8")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) == 3 and sys.argv[1] == "quests":
        arg = sys.argv[2]
        src = Path(arg) if arg.endswith(".toml") else PACK / "quests-src" / f"{arg}.toml"
        name = "quests_" + ("draft_" if "drafts" in src.parts else "") + src.stem
        render_quests(src, OUT / f"{name}.png")
        print("wrote", OUT / f"{name}.png", "and", OUT / f"{name}.drawio")
        sys.exit(0)
    import tempfile
    work = Path(tempfile.mkdtemp(prefix="gtia-flowcharts-"))
    for spec in sorted(SRC.glob("*.toml")):
        png = work / (spec.stem + ".png")
        render(tomllib.loads(spec.read_text(encoding="utf-8")), png)
        (OUT / png.name).write_bytes(png.read_bytes())
        print("wrote", OUT / png.name)
