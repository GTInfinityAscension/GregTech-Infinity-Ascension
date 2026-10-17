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

# EN: GTIA_BENCH_PRISM_DIR runs a second Prism (own data dir, instance "GTIA bench" sharing the pack's minecraft/),
#     so heap flags can change and that Prism can close while the author's Prism keeps running.
# PT: GTIA_BENCH_PRISM_DIR usa uma segunda Prism (pasta própria, instância "GTIA bench" com o minecraft/ do pack),
#     para mudar o heap e fechar essa Prism sem tocar na Prism do autor.
# ZH: 设置 GTIA_BENCH_PRISM_DIR 时使用第二个 Prism（独立数据目录，"GTIA bench" 实例共享整合包的 minecraft/），
#     可修改堆参数并关闭它，而不影响作者正在运行的 Prism。
PRISM_DIR = os.environ.get("GTIA_BENCH_PRISM_DIR", "")
INSTANCE = (Path(PRISM_DIR) / "instances/GTIA bench" if PRISM_DIR
            else Path.home() / ".local/share/PrismLauncher/instances/GTIA (full pack)")
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
    """Only this instance's client; another instance (e.g. the author's GTNH on a server) is never touched."""
    return [(p, a) for p, a in procs() if "/java" in a.split(" ")[0] and INSTANCE.name in a]


def other_clients() -> list[tuple[int, str]]:
    return [(p, a) for p, a in procs()
            if "/java" in a.split(" ")[0] and "PrismLauncher/instances/" in a and INSTANCE.name not in a]


def prisms() -> list[int]:
    found = [(p, a) for p, a in procs() if a.startswith("prismlauncher")]
    if PRISM_DIR:
        return [p for p, a in found if PRISM_DIR in a]
    return [p for p, _ in found]


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
    # Prism is closed (so instance.cfg can be written) only when no other instance is running.
    if PRISM_DIR or not other_clients():
        for pid in prisms():
            stop(pid, 10)


CAPTURE = OUT.parent / "client-launch.json"
ENV: dict[str, str] = {}


def capture(pid: int) -> None:
    """Saves the exact java command Prism used, so --direct can replay it with other JVM flags."""
    args = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
    env = dict(e.split("=", 1) for e in Path(f"/proc/{pid}/environ").read_bytes().decode(errors="replace").split("\0")
               if "=" in e)
    CAPTURE.write_text(json.dumps({"args": [a.decode() for a in args if a], "cwd": os.readlink(f"/proc/{pid}/cwd"),
                                   "env": env}))


def launch_direct(heap: int, jvm_args: str) -> None:
    saved = json.loads(CAPTURE.read_text())
    args = [a for a in saved["args"] if not re.match(r"-Xm[xs]\d", a)]
    extra = [f"-Xmx{heap}m", "-Xms512m", "-XX:NativeMemoryTracking=summary", *jvm_args.split()]
    env = dict(saved["env"])
    for item in [a for a in jvm_args.split() if a.startswith("ENV:")]:
        key, value = item[4:].split("=", 1)
        env[key] = value
        extra.remove(item)
    subprocess.Popen([args[0], *extra, *args[1:]], cwd=saved["cwd"], env=env, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def set_cfg(heap: int, jvm_args: str = "") -> None:
    # The bench Prism's global config is our own copy: write the same keys there too.
    for cfg in ([CFG, Path(PRISM_DIR) / "prismlauncher.cfg"] if PRISM_DIR else [CFG]):
        write_cfg(cfg, heap, jvm_args)


def write_cfg(cfg: Path, heap: int, jvm_args: str) -> None:
    text = cfg.read_text()
    args = "-Dforgewrapper.skipHashCheck=true" + (" " + jvm_args if jvm_args else "")
    env = json.dumps(ENV).replace('"', '\\"')
    pairs = [("OverrideEnv", "true" if ENV else "false"), ("Env", f'"{env}"'), ("OverrideMemory", "true"), ("MaxMemAlloc", str(heap)), ("MinMemAlloc", "512"),
             ("OverrideJavaArgs", "true"), ("JvmArgs", f'"{args}"')]
    for key, value in pairs:
        if not re.search(rf"^{key}=", text, flags=re.M):
            text += f"\n{key}={value}"
    for key, value in pairs:
        text = re.sub(rf"^{key}=.*$", f"{key}={value}", text, flags=re.M)
    cfg.write_text(text)


def smaps_summary(pid: int) -> dict:
    """RSS in MB grouped by mapping: java heap/anon, GPU (/dev/dri, driver libs), other libraries, files."""
    groups: dict[str, int] = {}
    name = ""
    for line in Path(f"/proc/{pid}/smaps").read_text(errors="replace").splitlines():
        parts = line.split()
        if parts and "-" in parts[0] and len(parts) >= 5 and not parts[0].endswith(":"):
            path = parts[5] if len(parts) > 5 else ""
            if path.startswith("/dev/dri") or "drm" in path:
                name = "gpu_device"
            elif any(k in path for k in ("libnvidia", "dri/", "libLLVM", "radeonsi", "iris", "libGLX", "libEGL", "mesa")):
                name = "gpu_driver_libs"
            elif path.endswith(".so") or ".so." in path:
                name = "other_libs"
            elif path.startswith("["):
                name = path
            elif path:
                name = "files"
            else:
                name = "anon"
        elif line.startswith("Rss:"):
            groups[name] = groups.get(name, 0) + int(parts[1])
    return {k: v // 1024 for k, v in sorted(groups.items(), key=lambda kv: -kv[1])}


def jcmd(pid: int) -> str:
    return str(Path(os.readlink(f"/proc/{pid}/exe")).with_name("jcmd"))


def run(heap: int, world: str, wait: int, jvm_args: str = "", jfr_dump: str = "", direct: bool = False) -> dict:
    close_all()
    if direct:
        LOG.unlink(missing_ok=True)
        start = time.time()
        launch_direct(heap, jvm_args)
        result = {"label": f"direct-{heap}", "heap_limit_mb": heap, "jvm_args": jvm_args}
        return measure(result, start, wait, jfr_dump, heap)
    if prisms():
        result_note = "prism kept open (another instance running): heap from instance.cfg, not --heap"
    else:
        result_note = ""
        set_cfg(heap, jvm_args)
    LOG.unlink(missing_ok=True)
    start = time.time()
    prism = ["prismlauncher", "-d", PRISM_DIR] if PRISM_DIR else ["prismlauncher"]
    subprocess.Popen([*prism, "--launch", INSTANCE.name, "--world", world],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    result = {"label": f"world-{heap}", "heap_limit_mb": heap, "env": dict(ENV), "jvm_args": jvm_args}
    if result_note:
        result["note"] = result_note
    return measure(result, start, wait, jfr_dump, heap)


def measure(result: dict, start: float, wait: int, jfr_dump: str, heap: int) -> dict:
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
    if found and not CAPTURE.exists():
        capture(found[0][0])
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
        result["smaps_mb"] = smaps_summary(pid)
        nmt = subprocess.run([jcmd(pid), str(pid), "VM.native_memory", "summary"], capture_output=True,
                             text=True).stdout
        total = re.search(r"Total: reserved=\d+KB, committed=(\d+)KB", nmt)
        if total:
            result["jvm_committed_mb"] = int(total.group(1)) // 1024
            parts = re.findall(r"-\s+([A-Za-z ]+?) \(reserved=\d+KB, committed=(\d+)KB\)", nmt)
            result["nmt_mb"] = {k.strip(): int(v) // 1024 for k, v in parts if int(v) >= 20 * 1024}
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
    ap.add_argument("--direct", action="store_true",
                    help="replay the captured java command (no Prism); --heap and --jvm-args (ENV:K=V too) apply")
    ap.add_argument("--env", action="append", default=[], help="K=V environment variable for the client")
    args = ap.parse_args()
    ENV.update(e.split("=", 1) for e in args.env)
    backup = CFG.with_suffix(".cfg.bench-backup")
    close_all()
    shutil.copy2(CFG, backup)
    try:
        for heap in args.heap:
            r = run(heap, args.world, args.wait, args.jvm_args, args.jfr_dump, args.direct)
            print(json.dumps(r), flush=True)
            with open(OUT, "a") as f:
                f.write(json.dumps(r) + "\n")
    finally:
        close_all()
        shutil.copy2(backup, CFG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
