#!/usr/bin/env python3
"""Server -> client traffic with one player near N working machines (LDLib sync cost).

    GTIA_BENCH_PRISM_DIR=... net_bench.py --machines 0 500 [--seconds 60]

Boots the locked pack on a dedicated server, places N working LV furnaces with `gtialib bench grid`, connects the
bench Prism client (never the author's Prism), teleports the player next to the grid and reads the TCP bytes the
server sent on port 25565 (ss) over --seconds. Appends to ~/MineProjects/GTIA-arquivo/perf/net.jsonl.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

import client_bench as client
import perf_bench as bench
import server_smoke as smoke

OUT = Path.home() / "MineProjects/GTIA-arquivo/perf/net.jsonl"


def bytes_sent() -> int:
    text = subprocess.run(["ss", "-tinH", "sport", "= :25565"], capture_output=True, text=True).stdout
    return sum(int(v) for v in re.findall(r"bytes_sent:(\d+)", text))


def prepare(lock: dict) -> None:
    work = smoke.WORK
    for folder in ("mods", "world", "logs", "crash-reports"):
        shutil.rmtree(work / folder, ignore_errors=True)
    (work / "mods").mkdir()
    for entry in lock["mods"]:
        if entry["mod_id"] not in bench.client_only():
            shutil.copy2(smoke.CACHE / entry["filename"], work / "mods" / entry["filename"])
    shutil.rmtree(work / "config", ignore_errors=True)
    shutil.copytree(smoke.PACK / "config", work / "config")
    (work / "eula.txt").write_text("eula=true\n")
    (work / "server.properties").write_text(
        "online-mode=false\nlevel-seed=12345\nview-distance=6\nspawn-protection=0\nmax-tick-time=-1\n")


def wait_for(log: Path, pattern: str, timeout: float) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if re.search(pattern, log.read_text(errors="replace")):
            return True
        time.sleep(2)
    return False


def one(lock: dict, machines: int, seconds: int) -> dict:
    prepare(lock)
    log = smoke.WORK / "net.log"
    forge_args = f"libraries/net/minecraftforge/forge/1.20.1-{lock['forge']}/unix_args.txt"
    result = {"machines": machines, "seconds": seconds, "time": time.strftime("%Y-%m-%d %H:%M")}
    with open(log, "w") as handle:
        server = subprocess.Popen([smoke.JAVA_RUN, "-Xmx4G", f"@{forge_args}", "nogui"], cwd=smoke.WORK,
                                  stdin=subprocess.PIPE, stdout=handle, stderr=subprocess.STDOUT, text=True)
        try:
            if not wait_for(log, r"Done \([\d.]+s\)", smoke.TIMEOUT):
                return {**result, "error": "server did not start"}
            if machines:
                bench.send(server, f"gtialib bench grid gtceu:lv_electric_furnace {machines} minecraft:sand")
            client.close_all()
            client.set_cfg(4096)
            subprocess.Popen(["prismlauncher", "-d", client.PRISM_DIR, "--launch", client.INSTANCE.name,
                              "--server", "localhost:25565"], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
            if not wait_for(log, r"joined the game", 600):
                return {**result, "error": "client did not join"}
            player = re.search(r"(\w+) joined the game", log.read_text(errors="replace")).group(1)
            bench.send(server, f"tp {player} 20 206 20")
            time.sleep(30)  # chunks and the initial machine sync settle
            start = bytes_sent()
            time.sleep(seconds)
            sent = bytes_sent() - start
            result.update(kb_per_s=round(sent / 1024 / seconds, 1), kb_total=round(sent / 1024))
        finally:
            client.close_all()
            if server.poll() is None:
                bench.send(server, "stop")
                try:
                    server.wait(timeout=90)
                except subprocess.TimeoutExpired:
                    server.kill()
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--machines", type=int, nargs="+", default=[0, 500])
    ap.add_argument("--seconds", type=int, default=60)
    args = ap.parse_args()
    if not client.PRISM_DIR:
        raise SystemExit("set GTIA_BENCH_PRISM_DIR (a separate Prism) so the author's Prism is never touched")
    lock = json.loads(smoke.LOCK.read_text(encoding="utf-8"))
    smoke.install_server(lock["forge"])
    backup = client.CFG.with_suffix(".cfg.bench-backup")
    shutil.copy2(client.CFG, backup)
    try:
        for n in args.machines:
            r = one(lock, n, args.seconds)
            print(json.dumps(r), flush=True)
            OUT.parent.mkdir(parents=True, exist_ok=True)
            with open(OUT, "a") as f:
                f.write(json.dumps(r) + "\n")
    finally:
        shutil.copy2(backup, client.CFG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
