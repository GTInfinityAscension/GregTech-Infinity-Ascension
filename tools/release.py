#!/usr/bin/env python3
"""Build the release files of the pack. Used by flake.nix and by .github/workflows/package.yml.

    release.py curseforge OUT_DIR [--version V]   CurseForge zip (import it in Prism, CurseForge app, ATLauncher...)
    release.py server OUT_DIR [--version V]       server zip: configs + local jars + server-side packwiz metadata
                                                 + install scripts that fetch Forge and the CurseForge mods

--version overrides `version` in pack.toml for this build only (CI passes the release tag or `<version>-<sha>`).
Neither command needs the network: the CurseForge zip only references mods by id, and the server package downloads
Forge and the mods when the server owner runs its install script.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
SERVER_FILES = PACK / ".github" / "server"
SHIPPED = ("config", "defaultconfigs", "resourcepacks")


def packwiz() -> str:
    exe = shutil.which("packwiz")
    if not exe:
        raise SystemExit("packwiz not found (https://packwiz.infra.link/installation/)")
    return exe


def pack_info() -> dict[str, str]:
    text = (PACK / "pack.toml").read_text(encoding="utf-8")
    get = lambda key: re.search(rf'^{key} = "([^"]*)"', text, re.M).group(1)  # noqa: E731
    return {"name": get("name"), "version": get("version"), "forge": get("forge"), "minecraft": get("minecraft")}


def staged(version: str | None) -> Path:
    """A copy of the pack (without git or build output) with the requested version, refreshed."""
    work = Path(tempfile.mkdtemp(prefix="gtia-release-"))
    shutil.copytree(PACK, work, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "result", "server-result", "*.zip"))
    if version:
        toml = work / "pack.toml"
        toml.write_text(re.sub(r'^version = ".*"$', f'version = "{version}"', toml.read_text(), count=1, flags=re.M))
    subprocess.run([packwiz(), "refresh"], cwd=work, check=True, stdout=subprocess.DEVNULL)
    return work


def slug(name: str) -> str:
    return name.replace(" ", "-")


def cmd_curseforge(out: Path, version: str | None) -> Path:
    work = staged(version)
    info = pack_info() if not version else {**pack_info(), "version": version}
    target = out / f"{slug(info['name'])}-{info['version']}.zip"
    subprocess.run([packwiz(), "curseforge", "export", "-o", str(target)], cwd=work, check=True,
                   stdout=subprocess.DEVNULL)
    shutil.rmtree(work)
    return target


def cmd_server(out: Path, version: str | None) -> Path:
    work = staged(version)
    info = pack_info() if not version else {**pack_info(), "version": version}
    root = Path(tempfile.mkdtemp(prefix="gtia-server-"))
    for folder in SHIPPED:
        if (work / folder).exists():
            shutil.copytree(work / folder, root / folder, ignore=shutil.ignore_patterns(".gitkeep"))
    (root / "mods").mkdir()
    for jar in (work / "mods").glob("*.jar"):
        shutil.copy2(jar, root / "mods" / jar.name)
    # packwiz-installer metadata with the server-side remote mods only; the jars above are already in place.
    meta = root / "gtia-installer" / "pack"
    (meta / "mods").mkdir(parents=True)
    shutil.copy2(work / "pack.toml", meta / "pack.toml")
    (meta / "index.toml").write_text('hash-format = "sha256"\n')
    for toml in (work / "mods").glob("*.pw.toml"):
        if not re.search(r'^side = "client"$', toml.read_text(), re.M):
            shutil.copy2(toml, meta / "mods" / toml.name)
    subprocess.run([packwiz(), "refresh"], cwd=meta, check=True, stdout=subprocess.DEVNULL)
    for name in ("install.sh", "install.bat", "README-SERVER.md"):
        shutil.copy2(SERVER_FILES / name, root / name)
    (root / "install.sh").chmod(0o755)
    shutil.copy2(work / "LICENSE.txt", root / "LICENSE.txt")
    (root / "gtia-installer" / "versions.txt").write_text(
        f"pack={info['version']}\nminecraft={info['minecraft']}\nforge={info['forge']}\n")
    target = out / f"{slug(info['name'])}-server-{info['version']}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                info_entry = zipfile.ZipInfo.from_file(path, path.relative_to(root).as_posix())
                if path.name == "install.sh":
                    info_entry.external_attr = 0o755 << 16
                z.writestr(info_entry, path.read_bytes(), zipfile.ZIP_DEFLATED)
    shutil.rmtree(work)
    shutil.rmtree(root)
    return target


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=("curseforge", "server"))
    ap.add_argument("out", type=Path)
    ap.add_argument("--version")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    built = (cmd_curseforge if args.kind == "curseforge" else cmd_server)(args.out.resolve(), args.version)
    print(built)
    return 0


if __name__ == "__main__":
    sys.exit(main())
