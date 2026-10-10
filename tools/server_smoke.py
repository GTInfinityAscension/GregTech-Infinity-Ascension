#!/usr/bin/env python3
"""Boot a dedicated Forge server with exactly the locked mods and report whether it loads.

    server_smoke.py            install the server once, copy the locked mods and config, start, wait for "Done", stop
    GTIA_PROFILE=first-slice server_smoke.py   the same with the small subset (default profile: full)
    server_smoke.py --export-recipes   also have GTIACore write every loaded recipe, item and fluid of the full pack
                                       to manifest/registry/pack/ (used by questgen's reachability check)

Run `pack.py fetch` first (this tool reads the mod cache). The server lives outside the repository, in
GTIA_SMOKE_DIR (default ~/MineProjects/GTIA-arquivo/server-smoke). It is a smoke test: a server never loads
client-only code, so the screen, the EMI line and rendering still need a real client.

The Forge installer fails on a processor hash with Java 17 on this machine and succeeds with Java 21, so the
installer runs on JAVA_INSTALL (default /usr/lib/jvm/java-21-openjdk) and the server on JAVA_RUN (default
Prism's Java 17, the one the clean instance uses).
"""

from __future__ import annotations

import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
PROFILE = os.environ.get("GTIA_PROFILE", "full")
LOCK = PACK / "manifest" / f"{PROFILE}.lock.json"
CACHE = Path(os.environ.get("GTIA_MOD_CACHE", Path.home() / "MineProjects/GTIA-arquivo/mod-cache"))
WORK = Path(os.environ.get("GTIA_SMOKE_DIR", Path.home() / "MineProjects/GTIA-arquivo/server-smoke"))
JAVA_INSTALL = os.environ.get("JAVA_INSTALL", "/usr/lib/jvm/java-21-openjdk/bin/java")
JAVA_RUN = os.environ.get("JAVA_RUN", str(Path.home() / ".local/share/PrismLauncher/java/java-runtime-gamma/bin/java"))
TIMEOUT = int(os.environ.get("GTIA_SMOKE_TIMEOUT", "420"))
EXPORT = WORK / "export"
EXPORT_TARGET = PACK / "manifest" / "registry" / "pack"
EXPORT_FILES = ("recipes.jsonl", "machines.jsonl", "worldgen.jsonl", "items.txt", "fluids.txt")


def install_server(forge: str) -> None:
    args = WORK / "libraries/net/minecraftforge/forge" / f"1.20.1-{forge}" / "unix_args.txt"
    if args.exists():
        return
    installer = WORK / "forge-installer.jar"
    if not installer.exists():
        url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/1.20.1-{forge}/forge-1.20.1-{forge}-installer.jar"
        request = urllib.request.Request(url, headers={"User-Agent": "gtia-pack-tool"})  # the Forge maven rejects urllib's default
        with urllib.request.urlopen(request, timeout=120) as response, open(installer, "wb") as out:
            shutil.copyfileobj(response, out)
    result = subprocess.run([JAVA_INSTALL, "-jar", str(installer), "--installServer"], cwd=WORK,
                            capture_output=True, text=True, timeout=600)
    if not args.exists():
        raise SystemExit("Forge server install failed:\n" + result.stdout[-1500:])


def run_server(lock: dict, skip: set[str], export: bool = False) -> tuple[str, float, str]:
    """One boot with the locked mods minus `skip` (client-only mods). Returns (outcome, seconds, log text)."""
    for folder in ("mods", "config", "world", "logs", "crash-reports", "kubejs", "export"):
        shutil.rmtree(WORK / folder, ignore_errors=True)
    (WORK / "mods").mkdir()
    for entry in lock["mods"]:
        if entry["mod_id"] in skip:
            continue
        source = CACHE / entry["filename"]
        if not source.exists():
            raise SystemExit(f"{source} is missing; run `pack.py fetch` first")
        shutil.copy2(source, WORK / "mods" / entry["filename"])
    test_config = Path.home() / ".local/share/PrismLauncher/instances/GregTech Infinity Ascension/minecraft/config"
    if PROFILE == "full" and test_config.exists():
        shutil.copytree(test_config, WORK / "config", dirs_exist_ok=True)  # same settings the instance gets
    shutil.copytree(PACK / "config", WORK / "config", dirs_exist_ok=True)
    (WORK / "eula.txt").write_text("eula=true\n")
    (WORK / "server.properties").write_text(
        "online-mode=false\nlevel-seed=12345\nmax-tick-time=-1\nview-distance=4\nspawn-protection=0\n")

    forge_args = f"libraries/net/minecraftforge/forge/1.20.1-{lock['forge']}/unix_args.txt"
    log = WORK / "smoke.log"
    with open(log, "w") as out:
        jvm = [f"-Dgtia.exportRecipes={EXPORT}"] if export else []
        server = subprocess.Popen([JAVA_RUN, *jvm, "@user_jvm_args.txt", f"@{forge_args}", "nogui"], cwd=WORK,
                                  stdin=subprocess.PIPE, stdout=out, stderr=subprocess.STDOUT, text=True)
        started = time.time()
        outcome = "timeout"
        while time.time() - started < TIMEOUT:
            if server.poll() is not None:
                outcome = "exited early"
                break
            text = log.read_text(errors="replace")
            if re.search(r"Done \(", text) and (not export or "Recipe export wrote" in text
                                                  or "Recipe export to" in text):
                outcome = "done"
                break
            time.sleep(2)
        if server.poll() is None:
            server.stdin.write("stop\n")
            server.stdin.flush()
            try:
                server.wait(timeout=60)
            except subprocess.TimeoutExpired:
                server.kill()
    return outcome, time.time() - started, log.read_text(errors="replace")


def main() -> int:
    export = "--export-recipes" in sys.argv[1:]
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    WORK.mkdir(parents=True, exist_ok=True)
    install_server(lock["forge"])
    known = {entry["mod_id"] for entry in lock["mods"]}
    skipped: list[str] = []
    for _ in range(8):
        outcome, seconds, text = run_server(lock, set(skipped), export)
        # A client-only mod cannot be constructed on a dedicated server. A real server pack leaves those out, so
        # leave out exactly the mods Forge names, then try again.
        failed = [m for m in re.findall(r"Failed to create mod instance\. ModID: (\w+)", text)
                  if m in known and m not in skipped]
        if outcome == "done" or not failed:
            break
        skipped.extend(failed)
    errors = [line for line in text.splitlines() if "/ERROR]" in line or "/FATAL]" in line]
    print(f"server: {outcome} in {seconds:.0f}s; mods: {len(lock['mods']) - len(skipped)} of {len(lock['mods'])}; "
          f"log: {WORK / 'smoke.log'}")
    if skipped:
        print("left out because they are client-only (cannot be constructed on a dedicated server):", ", ".join(skipped))
    if export:
        missing = [name for name in EXPORT_FILES if not (EXPORT / name).exists()]
        if outcome != "done" or missing:
            print("recipe export FAILED; missing:", ", ".join(missing) or "(server did not finish)")
            return 1
        EXPORT_TARGET.mkdir(parents=True, exist_ok=True)
        for name in EXPORT_FILES:
            if name == "recipes.jsonl":  # 25 MB as text; compressed it is small enough to keep in the repository
                with open(EXPORT / name, "rb") as raw, gzip.GzipFile(EXPORT_TARGET / (name + ".gz"), "wb", mtime=0) as out:
                    shutil.copyfileobj(raw, out)
            else:
                shutil.copy2(EXPORT / name, EXPORT_TARGET / name)
        recipes = sum(1 for _ in open(EXPORT / "recipes.jsonl", encoding="utf-8"))
        print(f"exported {recipes} recipes to {EXPORT_TARGET.relative_to(PACK)}")
    print(f"{len(errors)} ERROR/FATAL line(s)")
    for line in errors[:25]:
        print("  ", line[:200])
    return 0 if outcome == "done" and not any("/FATAL]" in line for line in errors) else 1


if __name__ == "__main__":
    sys.exit(main())
