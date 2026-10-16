#!/usr/bin/env python3
"""Measure a dedicated server boot of the locked pack: time to "Done", process RAM and live heap after a GC.

    perf_bench.py LABEL [--runs N] [--extra DIR] [--jvm "-Xmx3G ..."] [--tick ns:machine:count[:ns:item]] [--replace mod=jar] [--off feature]

Each run appends one JSON line to ~/MineProjects/GTIA-arquivo/perf/LABEL.jsonl and the script prints the median.
--extra copies every jar of DIR into mods/ on top of the lock (to measure a candidate mod before it is locked).
Uses the server installed by server_smoke.py and leaves out the mods in manifest/client-only.txt.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import statistics
import subprocess
import time
from pathlib import Path

import server_smoke as smoke

OUT = Path.home() / "MineProjects/GTIA-arquivo/perf"
JCMD = Path(smoke.JAVA_RUN).with_name("jcmd")


def client_only() -> set[str]:
    path = smoke.PACK / "manifest" / "client-only.txt"
    if not path.exists():
        return set()
    return {line.split("#")[0].strip() for line in path.read_text().splitlines() if line.split("#")[0].strip()}


def rss_mb(pid: int) -> float:
    for line in Path(f"/proc/{pid}/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) / 1024
    return 0.0


def heap_after_gc_mb(pid: int, histogram: Path | None) -> float:
    # A class histogram forces a full GC, so the heap measured right after it is the live set.
    hist = subprocess.run([str(JCMD), str(pid), "GC.class_histogram"], capture_output=True, text=True,
                          timeout=300).stdout
    if histogram:
        histogram.write_text("\n".join(hist.splitlines()[:80]))
    info = subprocess.run([str(JCMD), str(pid), "GC.heap_info"], capture_output=True, text=True, timeout=60).stdout
    used = re.search(r"used (\d+)K", info)
    return int(used.group(1)) / 1024 if used else 0.0


def send(server: subprocess.Popen, command: str) -> None:
    server.stdin.write(command + "\n")
    server.stdin.flush()


def tick_measure(server: subprocess.Popen, log: Path, spec: str) -> dict:
    """spec = 'ns:machine:count[:ns:input_item]'. With an input item the machines are kept running."""
    parts = spec.split(":")
    machine, count, item = ":".join(parts[:2]), parts[2], ":".join(parts[3:])
    send(server, f"gtialib bench grid {machine} {count} {item}".strip())
    time.sleep(20)  # let chunks load and machines settle
    send(server, "gtialib bench mspt 1200")
    deadline = time.time() + 300
    while time.time() < deadline:
        found = re.search(r"BENCH mspt=([\d.]+) worst=([\d.]+)", log.read_text(errors="replace"))
        if found:
            return {"tick_bench": spec, "mspt": float(found.group(1)), "worst_ms": float(found.group(2))}
        time.sleep(2)
    return {"tick_bench": spec, "mspt": None}


def one_run(lock: dict, skip: set[str], extra: Path | None, jvm: list[str], histogram: Path | None = None,
            tick_bench: str | None = None, replace: dict[str, Path] | None = None, off: list[str] | None = None) -> dict:
    # Prepare mods/config exactly like the smoke test, then start the server ourselves to measure it.
    work = smoke.WORK
    for folder in ("mods", "world", "logs", "crash-reports"):
        shutil.rmtree(work / folder, ignore_errors=True)
    (work / "mods").mkdir()
    replace = replace or {}
    for entry in lock["mods"]:
        if entry["mod_id"] in skip:
            continue
        if entry["mod_id"] in replace:
            shutil.copy2(replace[entry["mod_id"]], work / "mods" / replace[entry["mod_id"]].name)
        else:
            shutil.copy2(smoke.CACHE / entry["filename"], work / "mods" / entry["filename"])
    if extra:
        for jar in extra.glob("*.jar"):
            shutil.copy2(jar, work / "mods" / jar.name)
    shutil.rmtree(work / "config", ignore_errors=True)
    shutil.copytree(smoke.PACK / "config", work / "config")
    if off:
        (work / "config" / "ascopt-mixins.properties").write_text("".join(f"{f}=false\n" for f in off))
    (work / "eula.txt").write_text("eula=true\n")
    (work / "server.properties").write_text(
        "online-mode=false\nlevel-seed=12345\nmax-tick-time=-1\nview-distance=4\nspawn-protection=0\n")
    forge_args = f"libraries/net/minecraftforge/forge/1.20.1-{lock['forge']}/unix_args.txt"
    log = work / "bench.log"
    with open(log, "w") as out:
        server = subprocess.Popen([smoke.JAVA_RUN, *jvm, f"@{forge_args}", "nogui"], cwd=work,
                                  stdin=subprocess.PIPE, stdout=out, stderr=subprocess.STDOUT, text=True)
        started = time.time()
        result = {"outcome": "timeout"}
        while time.time() - started < smoke.TIMEOUT:
            if server.poll() is not None:
                result["outcome"] = "exited early"
                break
            text = log.read_text(errors="replace")
            done = re.search(r"Done \(([\d.]+)s\)", text)
            if done:
                if tick_bench:
                    result_tick = tick_measure(server, log, tick_bench)
                result = {"outcome": "done", "wall_s": round(time.time() - started, 1),
                          "done_s": float(done.group(1)), "rss_mb": round(rss_mb(server.pid)),
                          "heap_after_gc_mb": round(heap_after_gc_mb(server.pid, histogram)),
                          "mods": len(list((work / "mods").glob("*.jar")))}
                if tick_bench:
                    result.update(result_tick)
                break
            time.sleep(1)
        if server.poll() is None:
            server.stdin.write("stop\n")
            server.stdin.flush()
            try:
                server.wait(timeout=90)
            except subprocess.TimeoutExpired:
                server.kill()
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("label")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--extra", type=Path)
    ap.add_argument("--jvm", default="-Xms1G -Xmx4G")
    ap.add_argument("--replace", action="append", default=[], help="mod_id=path/to.jar instead of the locked jar")
    ap.add_argument("--remove", action="append", default=[], help="locked mod_id to leave out")
    ap.add_argument("--off", action="append", default=[], help="Ascension Optimizer feature to turn off")
    ap.add_argument("--tick", help="machine_id:count, e.g. gtceu:lv_electric_furnace:2000 (needs GTIA Lib)")
    args = ap.parse_args()
    lock = json.loads(smoke.LOCK.read_text(encoding="utf-8"))
    smoke.install_server(lock["forge"])
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for i in range(args.runs):
        r = one_run(lock, client_only() | set(args.remove), args.extra, args.jvm.split(), OUT / f"{args.label}-histogram.txt", args.tick,
                    {k: Path(v) for k, v in (r.split("=", 1) for r in args.replace)}, args.off)
        r.update(label=args.label, run=i + 1, jvm=args.jvm, time=time.strftime("%Y-%m-%d %H:%M"))
        print(json.dumps(r))
        with open(OUT / f"{args.label}.jsonl", "a") as f:
            f.write(json.dumps(r) + "\n")
        results.append(r)
    ok = [r for r in results if r["outcome"] == "done"]
    if not ok:
        print("no run finished; see", smoke.WORK / "bench.log")
        return 1
    for key in ("wall_s", "done_s", "rss_mb", "heap_after_gc_mb", "mspt"):
        values = [r[key] for r in ok if r.get(key) is not None]
        if values:
            print(f"median {key}: {statistics.median(values)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
