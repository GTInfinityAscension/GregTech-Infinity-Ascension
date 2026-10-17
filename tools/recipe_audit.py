#!/usr/bin/env python3
"""Boot the locked pack on a dedicated server, run `/gtia audit recipes` and copy the report.

    recipe_audit.py [OUT]

Lists every loaded recipe, from any mod, with an item input that resolves to nothing (an empty EMI slot).
Default OUT: ~/MineProjects/GTIA-arquivo/audits/recipe-audit-<date>.txt
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import perf_bench as bench
import server_smoke as smoke


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path.home() / f"MineProjects/GTIA-arquivo/audits/recipe-audit-{time.strftime('%Y-%m-%d')}.txt")
    lock = json.loads(smoke.LOCK.read_text(encoding="utf-8"))
    smoke.install_server(lock["forge"])
    work = smoke.WORK
    for folder in ("mods", "world", "logs", "crash-reports"):
        shutil.rmtree(work / folder, ignore_errors=True)
    (work / "mods").mkdir()
    skip = bench.client_only()
    for entry in lock["mods"]:
        if entry["mod_id"] not in skip:
            shutil.copy2(smoke.CACHE / entry["filename"], work / "mods" / entry["filename"])
    shutil.rmtree(work / "config", ignore_errors=True)
    shutil.copytree(smoke.PACK / "config", work / "config")
    (work / "eula.txt").write_text("eula=true\n")
    (work / "server.properties").write_text("online-mode=false\nlevel-seed=12345\nview-distance=4\n")
    report = work / "gtia-recipe-audit.txt"
    report.unlink(missing_ok=True)
    log = work / "audit.log"
    forge_args = f"libraries/net/minecraftforge/forge/1.20.1-{lock['forge']}/unix_args.txt"
    with open(log, "w") as handle:
        server = subprocess.Popen([smoke.JAVA_RUN, "-Xmx4G", f"@{forge_args}", "nogui"], cwd=work,
                                  stdin=subprocess.PIPE, stdout=handle, stderr=subprocess.STDOUT, text=True)
        started, sent = time.time(), False
        while time.time() - started < smoke.TIMEOUT and server.poll() is None:
            if not sent and re.search(r"Done \([\d.]+s\)", log.read_text(errors="replace")):
                bench.send(server, "gtia audit recipes")
                sent = True
            if report.exists() and "GTIA recipe audit" in log.read_text(errors="replace"):
                break
            time.sleep(1)
        if server.poll() is None:
            bench.send(server, "stop")
            try:
                server.wait(timeout=90)
            except subprocess.TimeoutExpired:
                server.kill()
    if not report.exists():
        print("no report; see", log)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(report, out)
    print(out)
    print("".join(line for line in report.read_text().splitlines(keepends=True) if line.startswith("#")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
