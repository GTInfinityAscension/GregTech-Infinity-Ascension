#!/usr/bin/env python3
"""Client memory benchmark on the Prism instance "GTIA (full pack)": join a world and measure live heap and RSS.

    client_bench.py --heap 4096 3072 2560 2048 [--world bench] [--wait 60]

For each heap limit: closes Prism, writes the limit to instance.cfg (Prism rewrites that file when it exits, so it is
only written while Prism is closed), launches with --world, waits for the player to join, waits --wait seconds, forces
a full GC and records live heap and RSS to ~/MineProjects/GTIA-arquivo/perf/client.jsonl. Processes are found in
/proc and killed by PID only. The original instance.cfg is restored at the end.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path

INSTANCE = Path.home() / ".local/share/PrismLauncher/instances/GTIA (full pack)"
CFG = INSTANCE / "instance.cfg"
LOG = INSTANCE / "minecraft/logs/latest.log"
OUT = Path.home() / "MineProjects/GTIA-arquivo/perf/client.jsonl"


def procs() -> list[tuple[int, str]]:
    found = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            args = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        found.append((int(pid), args))
    return found


def clients() -> list[tuple[int, str]]:
    return [(p, a) for p, a in procs() if "forgewrapper" in a and "/java" in a.split(" ")[0]]


def prisms() -> list[int]:
    return [p for p, a in procs() if a.startswith("prismlauncher")]


def stop(pid: int, wait: float = 30) -> None:
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    end = time.time() + wait
    while time.time() < end and Path(f"/proc/{pid}").exists():
        time.sleep(1)
    if Path(f"/proc/{pid}").exists():
        os.kill(pid, signal.SIGKILL)


def close_all() -> None:
    for pid, _ in clients():
        stop(pid)
    for pid in prisms():
        stop(pid, 10)


def set_cfg(heap: int, jvm_args: str = "") -> None:
    text = CFG.read_text()
    args = "-Dforgewrapper.skipHashCheck=true" + (" " + jvm_args if jvm_args else "")
    pairs = [("OverrideMemory", "true"), ("MaxMemAlloc", str(heap)), ("MinMemAlloc", "512"),
             ("OverrideJavaArgs", "true"), ("JvmArgs", f'"{args}"')]
    for key, value in pairs:
        if not re.search(rf"^{key}=", text, flags=re.M):
            text += f"\n{key}={value}"
    for key, value in pairs:
        text = re.sub(rf"^{key}=.*$", f"{key}={value}", text, flags=re.M)
    CFG.write_text(text)


def jcmd(pid: int) -> str:
    return str(Path(os.readlink(f"/proc/{pid}/exe")).with_name("jcmd"))


def run(heap: int, world: str, wait: int, jvm_args: str = "", jfr_dump: str = "") -> dict:
    close_all()
    set_cfg(heap, jvm_args)
    LOG.unlink(missing_ok=True)
    start = time.time()
    subprocess.Popen(["prismlauncher", "--launch", "GTIA (full pack)", "--world", world],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    result = {"label": f"world-{heap}", "heap_limit_mb": heap}
    while time.time() - start < 600:
        text = LOG.read_text(errors="replace") if LOG.exists() else ""
        if re.search(r"joined the game|FATAL|OutOfMemoryError", text):
            break
        time.sleep(2)
    result["joined_s"] = round(time.time() - start)
    time.sleep(wait)
    text = LOG.read_text(errors="replace") if LOG.exists() else ""
    result["joined"] = "joined the game" in text
    result["oom"] = text.count("OutOfMemoryError")
    result["fatal"] = text.count("FATAL")
    found = clients()
    if len(found) != 1:
        result["error"] = f"{len(found)} clients running"
    if found:
        pid, args = found[0]
        xmx = re.search(r"-Xmx(\d+)m", args)
        result["xmx_mb"] = int(xmx.group(1)) if xmx else None
        if jfr_dump:
            subprocess.run([jcmd(pid), str(pid), "JFR.dump", f"filename={jfr_dump}"], capture_output=True, timeout=300)
        hist = subprocess.run([jcmd(pid), str(pid), "GC.class_histogram"], capture_output=True, text=True,
                              timeout=300).stdout
        (OUT.parent / f"client-world-{heap}-histogram.txt").write_text("\n".join(hist.splitlines()[:80]))
        info = subprocess.run([jcmd(pid), str(pid), "GC.heap_info"], capture_output=True, text=True).stdout
        used = re.search(r"used (\d+)K", info)
        result["live_heap_mb"] = int(used.group(1)) // 1024 if used else None
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                result["rss_mb"] = int(line.split()[1]) // 1024
    close_all()
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--heap", type=int, nargs="+", required=True)
    ap.add_argument("--world", default="bench")
    ap.add_argument("--wait", type=int, default=60)
    ap.add_argument("--jvm-args", default="", help="extra JVM arguments for the client")
    ap.add_argument("--jfr-dump", default="", help="with a JFR recording in --jvm-args, dump it here after joining")
    args = ap.parse_args()
    backup = CFG.with_suffix(".cfg.bench-backup")
    close_all()
    shutil.copy2(CFG, backup)
    try:
        for heap in args.heap:
            r = run(heap, args.world, args.wait, args.jvm_args, args.jfr_dump)
            print(json.dumps(r), flush=True)
            with open(OUT, "a") as f:
                f.write(json.dumps(r) + "\n")
    finally:
        close_all()
        shutil.copy2(backup, CFG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
