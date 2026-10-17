#!/usr/bin/env python3
"""Write the packwiz metadata (mods/*.pw.toml) from manifest/full.lock.json, then run `packwiz refresh`.

    packwiz_sync.py            write mods/*.pw.toml, copy the local jars (gtia, gtna) into mods/, refresh the index
    packwiz_sync.py --check    only report differences; exit 1 if mods/ does not match the lock

The lockfile stays the source of truth for `pack.py` (instance, verify); packwiz is how the pack is distributed
(CurseForge export, packwiz-installer, server package). Every remote mod is written with the exact CurseForge file
of the lock and the SHA-1 of the cached jar, so packwiz never resolves a different version or a new dependency.
Local builds are shipped as jars inside mods/, like GTOCore in GregTech Odyssey.

`manifest/client-only.txt` lists the mods a dedicated server must not load (`side = "client"`); `server_smoke.py`
prints them as "left out because they are client-only". `manifest/server-only.txt` lists mods only the server
loads (`side = "server"`), left out of the client export.
"""

from __future__ import annotations

import hashlib
import json
import re
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
LOCK = PACK / "manifest" / "full.lock.json"
CLIENT_ONLY = PACK / "manifest" / "client-only.txt"
SERVER_ONLY = PACK / "manifest" / "server-only.txt"
MODS = PACK / "mods"
CACHE = Path(os.environ.get("GTIA_MOD_CACHE", Path.home() / "MineProjects" / "GTIA-arquivo" / "mod-cache"))


def display_name(jar: Path, fallback: str) -> str:
    try:
        with zipfile.ZipFile(jar) as z:
            text = z.read("META-INF/mods.toml").decode("utf-8", "replace")
    except (KeyError, zipfile.BadZipFile):
        return fallback
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("displayName"):
            value = line.split("=", 1)[1].strip()
            # Keep only the quoted string: some mods.toml put a comment after it (displayName="X" #mandatory).
            quoted = re.match(r'"([^"]*)"|\'([^\']*)\'', value)
            value = next(g for g in quoted.groups() if g is not None) if quoted else value
            if value and "${" not in value:
                return value
    return fallback


def quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


# EN: Local builds whose licence forbids shipping the jar: packwiz downloads them from Modrinth instead.
# PT: Builds locais cuja licença proíbe redistribuir o jar: o packwiz baixa do Modrinth.
# ZH: 许可证禁止再分发 jar 的本地构建：由 packwiz 从 Modrinth 下载。
MODRINTH = {
    "productivebees": ("jH6iiqkd", "mywVOObd",
                       "https://cdn.modrinth.com/data/jH6iiqkd/versions/mywVOObd/productivebees-1.20.1-12.6.0.jar"),
}


def expected() -> dict[str, str | Path]:
    """File name in mods/ -> .pw.toml text, or -> the local jar to copy."""
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    client = {line.split("#", 1)[0].strip() for line in CLIENT_ONLY.read_text().splitlines()} - {""}
    server = {line.split("#", 1)[0].strip() for line in SERVER_ONLY.read_text().splitlines()} - {""}
    files: dict[str, str | Path] = {}
    for mod in lock["mods"]:
        jar = CACHE / mod["filename"]
        if mod["mod_id"] in MODRINTH:
            project, version, url = MODRINTH[mod["mod_id"]]
            files[f"{mod['mod_id']}.pw.toml"] = (
                f"name = {quote(display_name(jar, mod['mod_id']))}\n"
                f"filename = {quote(mod['filename'])}\n"
                "side = \"both\"\n\n"
                "[download]\n"
                f"url = {quote(url)}\n"
                "hash-format = \"sha1\"\n"
                f"hash = \"{hashlib.sha1(jar.read_bytes()).hexdigest()}\"\n\n"
                "[update]\n"
                "[update.modrinth]\n"
                f"mod-id = \"{project}\"\n"
                f"version = \"{version}\"\n"
            )
            continue
        if mod["source"] == "local-build":
            files[mod["filename"]] = jar
            continue
        if not jar.exists():
            raise SystemExit(f"missing in cache: {jar} (run `python3 tools/pack.py fetch`)")
        sha1 = hashlib.sha1(jar.read_bytes()).hexdigest()
        side = "client" if mod["mod_id"] in client else "server" if mod["mod_id"] in server else "both"
        files[f"{mod['mod_id']}.pw.toml"] = (
            f"name = {quote(display_name(jar, mod['mod_id']))}\n"
            f"filename = {quote(mod['filename'])}\n"
            f"side = \"{side}\"\n\n"
            "[download]\n"
            "hash-format = \"sha1\"\n"
            f"hash = \"{sha1}\"\n"
            "mode = \"metadata:curseforge\"\n\n"
            "[update]\n"
            "[update.curseforge]\n"
            f"file-id = {mod['file_id']}\n"
            f"project-id = {mod['project_id']}\n"
        )
    return files


def same(path: Path, want: str | Path) -> bool:
    if not path.exists():
        return False
    if isinstance(want, Path):
        return path.read_bytes() == want.read_bytes()
    return path.read_text(encoding="utf-8") == want


def main() -> int:
    check = "--check" in sys.argv[1:]
    want = expected()
    have = {p.name for p in MODS.glob("*") if p.is_file()} if MODS.exists() else set()
    stale = sorted(have - set(want))
    changed = sorted(name for name, content in want.items() if not same(MODS / name, content))
    if check:
        for name in changed:
            print("differs from the lock:", name)
        for name in stale:
            print("not in the lock:", name)
        print(f"mods/: {len(want)} expected, {len(changed)} differ, {len(stale)} extra")
        return 1 if changed or stale else 0
    MODS.mkdir(exist_ok=True)
    for name in stale:
        (MODS / name).unlink()
    for name in changed:
        content = want[name]
        if isinstance(content, Path):
            shutil.copy2(content, MODS / name)
        else:
            (MODS / name).write_text(content, encoding="utf-8")
    print(f"mods/: wrote {len(changed)}, removed {len(stale)}, {len(want)} in total")
    packwiz = shutil.which("packwiz")
    if not packwiz:
        print("packwiz not found; run `packwiz refresh` yourself")
        return 1
    (PACK / "index.toml").touch()
    return subprocess.run([packwiz, "refresh"], cwd=PACK).returncode


if __name__ == "__main__":
    raise SystemExit(main())
