#!/usr/bin/env python3
"""Build a Modrinth pack (.mrpack) of the locked mods, for Android launchers such as Amethyst (GTNH does the same).

    mrpack.py OUT_DIR [--version V] [--include-unlisted]

- Mods whose exact jar (same SHA-1) is on Modrinth are referenced by link, as the format requires.
- The organisation's own mods (local builds, LGPL-3.0) ship inside the pack as overrides.
- Mods only on CurseForge can't be linked (the format allows Modrinth/GitHub/GitLab links only) and are left out
  unless their licence allows redistribution (manifest/mrpack-redistributable.txt). They are printed at the end and
  written to OUT_DIR/missing-mods.txt so the pack stays honest about what is missing.
Server-only mods (manifest/server-only.txt) are left out, as in the client pack.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
MANIFEST = PACK / "manifest"
CACHE = Path.home() / "MineProjects/GTIA-arquivo/mod-cache"
API = "https://api.modrinth.com/v2"
UA = {"User-Agent": "GTInfinityAscension/mrpack-tool", "Content-Type": "application/json"}


def read_list(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {line.split("#", 1)[0].strip() for line in path.read_text().splitlines()} - {""}


def modrinth_files(sha1s: list[str]) -> dict:
    request = urllib.request.Request(f"{API}/version_files", headers=UA,
                                     data=json.dumps({"hashes": sha1s, "algorithm": "sha1"}).encode())
    return json.load(urllib.request.urlopen(request, timeout=60))


def alternative_file(alt: dict) -> dict:
    """The primary file of a given Modrinth project version (same mod version, different upload)."""
    request = urllib.request.Request(f"{API}/project/{alt['project']}/version", headers=UA)
    for version in json.load(urllib.request.urlopen(request, timeout=60)):
        if version["version_number"] == alt["version"]:
            file = next((f for f in version["files"] if f["primary"]), version["files"][0])
            return {"path": f"mods/{file['filename']}", "hashes": file["hashes"],
                    "env": {"client": "required", "server": "required"},
                    "downloads": [file["url"]], "fileSize": file["size"]}
    raise SystemExit(f"{alt['project']} {alt['version']} is no longer on Modrinth")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--version", default=None)
    args = ap.parse_args()
    lock = json.loads((MANIFEST / "full.lock.json").read_text())
    pack_toml = (PACK / "pack.toml").read_text()
    version = args.version or next(l.split('"')[1] for l in pack_toml.splitlines() if l.startswith("version"))
    server_only = read_list(MANIFEST / "server-only.txt")
    redistributable = read_list(MANIFEST / "mrpack-redistributable.txt")
    alternatives = {k: v for k, v in json.loads((MANIFEST / "mrpack-modrinth.json").read_text()).items()
                    if not k.startswith("_")} if (MANIFEST / "mrpack-modrinth.json").exists() else {}

    remote = [m for m in lock["mods"] if m["source"] != "local-build" and m["mod_id"] not in server_only]
    sha1 = {m["mod_id"]: hashlib.sha1((CACHE / m["filename"]).read_bytes()).hexdigest() for m in remote}
    found = modrinth_files(list(sha1.values()))

    files, overrides, missing = [], [], []
    for mod in remote:
        version_info = found.get(sha1[mod["mod_id"]])
        jar = CACHE / mod["filename"]
        if version_info:
            file = next(f for f in version_info["files"] if f["hashes"]["sha1"] == sha1[mod["mod_id"]])
            files.append({"path": f"mods/{file['filename']}", "hashes": file["hashes"],
                          "env": {"client": "required", "server": "required"},
                          "downloads": [file["url"]], "fileSize": file["size"]})
        elif mod["mod_id"] in alternatives:
            files.append(alternative_file(alternatives[mod["mod_id"]]))
        elif mod["mod_id"] in redistributable:
            overrides.append(jar)
        else:
            missing.append(mod)
    for mod in lock["mods"]:
        if mod["source"] == "local-build" and mod["mod_id"] not in server_only:
            overrides.append(Path(mod["path"]))

    index = {"formatVersion": 1, "game": "minecraft", "versionId": version,
             "name": "GregTech Infinity Ascension", "summary": "GregTech where the factory is the star",
             "files": files, "dependencies": {"minecraft": lock["minecraft"], "forge": lock["forge"]}}
    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out / f"GregTech-Infinity-Ascension-{version}.mrpack"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("modrinth.index.json", json.dumps(index, indent=2))
        for jar in overrides:
            z.write(jar, f"overrides/mods/{jar.name}")
        for folder in ("config", "defaultconfigs", "kubejs", "resourcepacks", "shaderpacks"):
            src = PACK / folder
            if src.is_dir():
                for path in src.rglob("*"):
                    if path.is_file():
                        z.write(path, f"overrides/{path.relative_to(PACK)}")
    (args.out / "missing-mods.txt").write_text(
        "".join(f"{m['mod_id']}\t{m['filename']}\thttps://www.curseforge.com/projects/{m.get('project_id', '')}\n"
                for m in missing))
    print(f"{target}: {len(files)} mods by Modrinth link ({len(alternatives)} of them a different upload of the same version), {len(overrides)} jars inside, "
          f"{len(missing)} left out (only on CurseForge): {', '.join(m['mod_id'] for m in missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
