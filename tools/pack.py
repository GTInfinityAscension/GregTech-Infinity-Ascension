#!/usr/bin/env python3
"""Reproducible base for the GTIA modpack: lock, fetch, verify and build a clean Prism instance.

    pack.py lock      resolve the profile's mods and their required dependencies into a lockfile
    pack.py fetch     fetch every locked mod into the cache, checking SHA-256 (local builds are copied)
    pack.py verify    check the cache (or a mods folder) against the lock
    pack.py instance  build a NEW Prism instance from the lock, the test instance's configs and this project's config
    pack.py sync      copy this project's config (quests, balance) over an existing instance (--instance NAME), backing up its quests first

Profiles (`--profile`): `full` (default) is the whole pack, every active mod of the audited inventory minus the ones
listed with a reason in manifest/full.exclude; `first-slice` is the small Start -> LV subset used for quick smoke tests.

Remote mods come from the audited inventory (`source-audit-*.tsv`), which records the CurseForge project and
file ids and the SHA-256 of the exact jar. They are downloaded through CurseMaven. GTIACore and GTNA are local
builds, so their hash changes with every rebuild: `lock` records the current one and `fetch` refuses a different
jar unless you pass `--accept-local`. Nothing here touches an existing instance.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
import time
import urllib.request
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
MANIFEST = PACK / "manifest"
ROOT = PACK.parent
AUDIT = MANIFEST / "source-audit-2026-09-29.tsv"
PROFILES = {
    "full": {"seeds": None, "exclude": MANIFEST / "full.exclude", "lock": MANIFEST / "full.lock.json",
             "instance": "GTIA (full pack)"},
    "first-slice": {"seeds": MANIFEST / "first-slice.seeds", "exclude": None,
                    "lock": MANIFEST / "first-slice.lock.json", "instance": "GTIA First Slice (clean)"},
}
PROFILE = PROFILES["full"]
CACHE = Path(os.environ.get("GTIA_MOD_CACHE", Path.home() / "MineProjects" / "GTIA-arquivo" / "mod-cache"))
PRISM = Path(os.environ.get("PRISM_INSTANCES", Path.home() / ".local/share/PrismLauncher/instances"))
TEMPLATE_INSTANCE = "GregTech Infinity Ascension"
BUILT_IN = {"forge", "minecraft"}

LOCAL_BUILDS = {
    "gtia": Path(os.environ.get("GTIA_JAR", ROOT / "core/build/libs/gtia-0.1.0.jar")),
    "gtna": Path(os.environ.get(
        "GTNA_JAR", Path.home() / "MineProjects/GregTech-Nexus-Addon/build/libs/gtna-0.6.0.jar")),
    # Shared library of the org's mods (GTIA-D-262); GTIACore and GTNA require it.
    "gtialib": Path(os.environ.get(
        "GTIALIB_JAR", ROOT.parent / "GTIA-arquivo/jar-backups/2026-10-16-gtialib-0.5.0/gtialib-0.5.0.jar")),
    # Measured performance fixes (GTIA-D-263).
    "ascopt": Path(os.environ.get(
        "ASCOPT_JAR", ROOT.parent / "GTIA-arquivo/jar-backups/2026-10-16-ascopt-0.2.0/ascopt-0.2.0.jar")),
    # Until ModernSpace 0.3.0 is on CurseForge, the GitHub release jar ships in the pack like the two above.
    "modernspace": Path(os.environ.get(
        "MODERNSPACE_JAR", ROOT.parent / "GTIA-arquivo/jar-backups/2026-10-11-modernspace-0.3.1/modernspace-0.3.1.jar")),
    # Org crop mod (GTIA-D-260, D-267); local build until its first release.
    "agronomica": Path(os.environ.get(
        "AGRONOMICA_JAR", Path.home() / "MineProjects/Agronomica/build/libs/agronomica-0.1.0.jar")),
    # Productive Bees for the HV bee line (GTIA-D-259, D-268), Modrinth jar kept in the archive.
    "productivebees": Path(os.environ.get(
        "PRODUCTIVEBEES_JAR",
        ROOT.parent / "GTIA-arquivo/jar-backups/2026-10-16-productivebees-12.6.0/productivebees-1.20.1-12.6.0.jar")),
    # Crafting Chain replaces Fabricate (GTIA-D-257); shipped in the pack until it is on CurseForge.
    "craftingchain": Path(os.environ.get(
        "CRAFTINGCHAIN_JAR",
        ROOT.parent / "GTIA-arquivo/jar-backups/2026-10-11-craftingchain-0.1.0/craftingchain-0.1.0.jar")),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def server_only_ids() -> set[str]:
    path = MANIFEST / "server-only.txt"
    return set(read_list(path)) if path.exists() else set()


def read_list(path: Path) -> list[str]:
    lines = [line.split("#", 1)[0].strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return [line.split()[0] for line in lines if line]


def read_seeds(audit: dict[str, dict]) -> list[str]:
    if PROFILE["seeds"] is not None:
        return read_list(PROFILE["seeds"])
    # Full pack: every mod id of every active jar, plus the local builds that replace the old ones.
    return sorted(set(audit) | set(LOCAL_BUILDS))


def read_excluded() -> set[str]:
    return set(read_list(PROFILE["exclude"])) if PROFILE["exclude"] else set()


def read_audit() -> dict[str, dict]:
    by_mod: dict[str, dict] = {}
    with open(AUDIT, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if row["status"] != "active":
                continue
            ids = [m.strip() for m in row["mod_ids"].split(",") if m.strip()]
            if not ids:
                # Language providers (for example kotlinforforge) are not mods, so the audit has no mod id for them.
                # Mods that need them name the provider, so key the row by the start of the file name.
                ids = [row["filename"].split("-")[0].lower()]
            for mod_id in ids:
                by_mod.setdefault(mod_id, row)
    return by_mod


def cmd_lock(_args) -> int:
    audit = read_audit()
    seeds = read_seeds(audit)
    excluded = read_excluded()
    mods: dict[str, dict] = {}
    unresolved: set[str] = set()
    blocked: set[str] = set()
    queue = [seed for seed in seeds if seed not in excluded]
    while queue:
        mod_id = queue.pop(0)
        if mod_id in mods or mod_id in BUILT_IN:
            continue
        if mod_id in excluded:
            blocked.add(mod_id)
            continue
        if mod_id in LOCAL_BUILDS:
            jar = LOCAL_BUILDS[mod_id]
            if not jar.exists():
                print(f"missing local build for {mod_id}: {jar}", file=sys.stderr)
                return 1
            mods[mod_id] = {"mod_id": mod_id, "filename": jar.name, "sha256": sha256(jar), "source": "local-build",
                            "path": str(jar), "requires": []}
            continue
        row = audit.get(mod_id)
        if row is None:
            unresolved.add(mod_id)
            continue
        requires = sorted(r for r in (x.strip() for x in row["required_mod_ids"].split(",")) if r and r not in BUILT_IN)
        mods[mod_id] = {"mod_id": mod_id, "filename": row["filename"], "sha256": row["sha256"],
                        "source": "curseforge", "project_id": int(row["project_id"]), "file_id": int(row["file_id"]),
                        "requires": requires}
        queue.extend(requires)
    # A jar can provide several mod ids; keep one entry per file.
    files: dict[str, dict] = {}
    for entry in mods.values():
        files.setdefault(entry["filename"], entry)
    # Dependencies that no jar provides are either bundled inside another jar or genuinely missing.
    provided = {m for e in mods.values() for m in [e["mod_id"]]}
    for entry in mods.values():
        for dependency in entry["requires"]:
            if dependency not in provided and dependency not in BUILT_IN:
                unresolved.add(dependency)
    lock = {
        "minecraft": "1.20.1",
        "forge": "47.4.23",
        "profile": next(name for name, value in PROFILES.items() if value is PROFILE),
        "seeds": seeds,
        "excluded": sorted(excluded),
        "mods": sorted(files.values(), key=lambda e: e["mod_id"]),
        "unresolved_dependencies": sorted(unresolved),
    }
    PROFILE["lock"].write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"locked {len(files)} jars from {len(seeds)} seeds -> {PROFILE['lock'].relative_to(ROOT)}")
    if blocked:
        print("excluded (see full.exclude):", ", ".join(sorted(blocked)))
    required_but_excluded = sorted({d for e in mods.values() for d in e["requires"] if d in excluded})
    if required_but_excluded:
        print("ERROR: kept mods require excluded mods:", ", ".join(required_but_excluded))
        return 1
    if unresolved:
        print("not provided by any jar (bundled inside another mod, or missing):", ", ".join(sorted(unresolved)))
    return 0


def read_lock() -> dict:
    if not PROFILE["lock"].exists():
        raise SystemExit("no lock yet: run `pack.py lock` first")
    return json.loads(PROFILE["lock"].read_text(encoding="utf-8"))


def url_of(entry: dict) -> str:
    slug = f"gtia-{entry['project_id']}"
    return f"https://www.cursemaven.com/curse/maven/{slug}/{entry['file_id']}/{slug}-{entry['file_id']}.jar"


def cmd_fetch(args) -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    bad = 0
    for entry in read_lock()["mods"]:
        target = CACHE / entry["filename"]
        if entry["source"] == "local-build":
            source = Path(entry["path"])
            if not source.exists():
                print(f"MISSING local build {source}")
                bad += 1
                continue
            if sha256(source) != entry["sha256"] and not args.accept_local:
                print(f"CHANGED {entry['filename']}: rebuilt since the lock; run `lock` again or pass --accept-local")
                bad += 1
                continue
            shutil.copy2(source, target)
            print(f"copied  {entry['filename']}")
            continue
        if target.exists() and sha256(target) == entry["sha256"]:
            print(f"cached  {entry['filename']}")
            continue
        # Same bytes already on disk in the test instance: reuse them instead of downloading again.
        sibling = PRISM / TEMPLATE_INSTANCE / "minecraft" / "mods" / entry["filename"]
        if sibling.exists() and sha256(sibling) == entry["sha256"]:
            shutil.copy2(sibling, target)
            print(f"reused  {entry['filename']}")
            continue
        if "file_id" not in entry:
            print(f"NO SOURCE for {entry['filename']}")
            bad += 1
            continue
        request = urllib.request.Request(url_of(entry), headers={"User-Agent": "gtia-pack-tool"})
        with urllib.request.urlopen(request, timeout=120) as response, open(target, "wb") as out:
            shutil.copyfileobj(response, out)
        if sha256(target) != entry["sha256"]:
            print(f"HASH MISMATCH {entry['filename']}")
            target.unlink()
            bad += 1
        else:
            print(f"fetched {entry['filename']}")
    return 1 if bad else 0


def cmd_verify(args) -> int:
    folder = Path(args.folder) if args.folder else CACHE
    lock = read_lock()
    problems = []
    names = {entry["filename"] for entry in lock["mods"]}
    for entry in lock["mods"]:
        path = folder / entry["filename"]
        if not path.exists():
            if args.folder and entry["mod_id"] in server_only_ids():
                continue  # a client instance leaves the server-only mods out on purpose
            problems.append(f"missing {entry['filename']}")
        elif sha256(path) != entry["sha256"]:
            problems.append(f"hash differs {entry['filename']}")
    if args.folder:
        for extra in sorted(p.name for p in folder.glob("*.jar") if p.name not in names):
            problems.append(f"not in the lock {extra}")
    for line in problems:
        print("ERROR:", line)
    if not problems:
        print(f"OK: {len(lock['mods'])} jars match the lock in {folder}")
    return 1 if problems else 0


def cmd_instance(args) -> int:
    lock = read_lock()
    name = PROFILE["instance"]
    target = PRISM / name
    template = PRISM / TEMPLATE_INSTANCE
    if target.exists():
        if not args.force:
            print(f"{target} already exists; pass --force to rebuild it (only that folder is deleted)")
            return 1
        shutil.rmtree(target)
    if cmd_fetch(argparse.Namespace(accept_local=args.accept_local)) != 0:
        return 1
    (target / "minecraft" / "mods").mkdir(parents=True)
    shutil.copy2(template / "mmc-pack.json", target / "mmc-pack.json")
    cfg = (template / "instance.cfg").read_text(encoding="utf-8")
    lines = [line for line in cfg.splitlines() if not line.startswith(("name=", "InstanceAccountId="))]
    lines.append(f"name={name}")
    (target / "instance.cfg").write_text("\n".join(lines) + "\n", encoding="utf-8")
    server_only = server_only_ids()
    for entry in lock["mods"]:
        if entry["mod_id"] in server_only:
            continue  # the client instance gets what the client pack gets
        shutil.copy2(CACHE / entry["filename"], target / "minecraft" / "mods" / entry["filename"])
    # Settings the pack has not moved into this project yet still live in the test instance. Copy the ones that
    # belong to the pack, never saves, logs, maps or personal files. The project's own config is laid on top.
    if args.with_test_config:
        for folder in ("config", "defaultconfigs", "packmenu", "resourcepacks"):
            source = template / "minecraft" / folder
            if source.exists():
                shutil.copytree(source, target / "minecraft" / folder, dirs_exist_ok=True)
    config = PACK / "config"
    if config.exists():
        shutil.copytree(config, target / "minecraft" / "config", dirs_exist_ok=True)
    kubejs = PACK / "kubejs"
    # Scripts and data only mean something when the KubeJS mod is part of the lock.
    has_kubejs = any(entry["mod_id"] == "kubejs" for entry in lock["mods"])
    if has_kubejs and kubejs.exists():
        shutil.copytree(kubejs, target / "minecraft" / "kubejs", dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".gitkeep"))
    print(f"built {target} with {len(lock['mods'])} mods")
    return cmd_verify(argparse.Namespace(folder=str(target / "minecraft" / "mods")))


def cmd_sync(args) -> int:
    """Refresh an instance with the project's own config. Saves, options and mods are left alone.

    Before replacing a file that differs, the instance's whole `config/ftbquests` is copied to
    GTIA-arquivo/config-backups, because quests can be edited in the game and those edits would be lost.
    """
    name = args.instance or PROFILE["instance"]
    target = PRISM / name / "minecraft"
    if not target.exists():
        print(f"{target} does not exist")
        return 1
    changes = []
    for source in sorted((PACK / "config").rglob("*")):
        if source.is_file() and source.name != ".gitkeep":
            destination = target / "config" / source.relative_to(PACK / "config")
            if not destination.exists() or sha256(destination) != sha256(source):
                changes.append((source, destination))
    if not changes:
        print(f"{name} is already up to date")
        return 0
    quests = target / "config" / "ftbquests"
    if quests.exists():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = Path.home() / "MineProjects" / "GTIA-arquivo" / "config-backups" / f"{name}-{stamp}" / "ftbquests"
        shutil.copytree(quests, backup)
        print(f"backup of the instance's quests: {backup}")
    for source, destination in changes:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        print(f"updated config/{source.relative_to(PACK / 'config')}")
    print(f"{len(changes)} file(s) updated in {name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", choices=sorted(PROFILES), default="full")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("lock").set_defaults(run=cmd_lock)
    fetch = sub.add_parser("fetch")
    fetch.add_argument("--accept-local", action="store_true")
    fetch.set_defaults(run=cmd_fetch)
    verify = sub.add_parser("verify")
    verify.add_argument("folder", nargs="?")
    verify.set_defaults(run=cmd_verify)
    instance = sub.add_parser("instance")
    instance.add_argument("--force", action="store_true")
    instance.add_argument("--accept-local", action="store_true")
    instance.add_argument("--no-test-config", dest="with_test_config", action="store_false",
                          help="do not copy config/ from the test instance (default: copy it for the full profile)")
    instance.set_defaults(run=cmd_instance, with_test_config=True)
    sync = sub.add_parser("sync")
    sync.add_argument("--instance", help="Prism instance name (default: the profile's instance)")
    sync.set_defaults(run=cmd_sync)
    args = parser.parse_args()
    global PROFILE
    PROFILE = PROFILES[args.profile]
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())
