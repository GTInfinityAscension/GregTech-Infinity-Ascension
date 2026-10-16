# GregTech Infinity Ascension (GTIA)

A GregTech modpack for Minecraft 1.20.1 built on **GTCEu Modern**, **[GregTech Nexus Addon (GTNA)](https://github.com/GTInfinityAscension/GregTech-Nexus-Addon)** and **[GTIACore](https://github.com/GTInfinityAscension/GTIACore)**.

GTIA is guided GregTech where the factory is the star: Satisfactory-style megafactories, real industrial chemistry and long production lines. You start in Steam, go electric, head to space and keep scaling. Large machines, wireless power and AE2 are part of the main path, not side content. The quest book is the main guide, and it's written with a sense of humour.

> **Status: early development.** Builds are for testers. Start → Steam → LV is the first slice we want people to play; see the [roadmap](ROADMAP.md) and the [Start/Steam/LV plan](docs/START_STEAM_LV_PLAN.md).

## Design pillars

- **Grind is solved with more factory**, never with more clicking.
- **Lines get longer every tier:** Steam 2–3 steps, LV/MV 4–6, HV/EV 6–10, IV+ 10+.
- **Real chemistry, no PhD:** wood distillation, lime kiln, chlor-alkali, Bayer + Hall-Héroult, Contact process, Haber-Bosch, Solvay... Important molecules have an early, expensive route and a later, efficient one.
- **No ULV era and no research tree.** The campaign goes Start → Steam → LV → MV → HV → ...
- **Every quest is reachable.** A checker reads the pack's real recipes and fails the build if a quest asks for something you can't make yet.
- **Modes:** Normal/Journey are picked at world creation and locked.

## How to play

Download the latest build from [Releases](https://github.com/GTInfinityAscension/GregTech-Infinity-Ascension/releases):

| File | Use it for |
| --- | --- |
| `GregTech-Infinity-Ascension-<version>.zip` | **Client.** Import it in Prism Launcher (*Add Instance → Import*), the CurseForge app or ATLauncher. |
| `GregTech-Infinity-Ascension-server-<version>.zip` | **Dedicated server.** Unzip, run `install.sh` / `install.bat`, see `README-SERVER.md`. |
| `GregTech-Infinity-Ascension-<version>.mrpack` | **Android** (Amethyst launcher). See the [mobile guide](docs/MOBILE.md). Coming soon. |

**Java 21** and 8 GB of RAM or more are recommended. Java 21 gives steadier frame times than Java 17; the pack also runs on Java 17. Java 25 is not supported yet (spark's profiler crashes on it). In Prism Launcher: *Edit Instance → Settings → Java*, pick a Java 21 install and set the memory there.

The pack ships the **CozyUI+** resource pack enabled by default and the **Complementary Reimagined** shaders (pick them in *Video Settings → Shader Packs*; Euphoria Patches are applied on top automatically).

### Release channels

| Channel | Tag | What to expect |
| --- | --- | --- |
| dev | `X.Y.Z-dev-N` | Snapshot for the team and testers. |
| pre | `X.Y.Z-pre-N` | Feature-complete for the version and being tested. |
| alpha | `X.Y.Z-alpha[-N]` | First public test of the version. |
| beta | `X.Y.Z-beta[-N]` | **Stable** for the version. |

A version moves dev → pre → alpha → beta. Only two releases are kept at a time: the newest beta and the newest dev/pre/alpha (a new one replaces the previous one of its group). Every change to `main` is also built by CI as a downloadable workflow artifact. Always say the exact version when reporting a bug.

### Other ways to install

- **packwiz-installer:** point [packwiz-installer](https://packwiz.infra.link/tutorials/installing/packwiz-installer/) at `pack.toml` from this repo (raw URL or a local clone) to install and auto-update an instance.
- **Export it yourself:** install [packwiz](https://github.com/packwiz/packwiz), clone the repo and run `packwiz curseforge export`.
- **Nix (flake):** see [Building with Nix](#building-with-nix).

### Building with Nix

The repo is a Nix flake (flakes must be enabled: `experimental-features = nix-command flakes`). Nothing is downloaded at build time besides the flake inputs, because the zips reference the mods instead of bundling them.

```sh
git clone https://github.com/GTInfinityAscension/GregTech-Infinity-Ascension.git
cd GregTech-Infinity-Ascension

nix build .#curseforge          # client zip  -> result/GregTech-Infinity-Ascension-<version>.zip
nix build .#server -o server    # server zip  -> server/GregTech-Infinity-Ascension-server-<version>.zip
nix develop                     # shell with packwiz, Python 3, JDK 17 and yq for working on the pack
```

`nix build .` is the same as `.#curseforge`. Each build leaves a `result` (or the name given with `-o`) symlink to the Nix store; copy the zip out of it before you change anything, because the next build replaces the link.

- **Client:** in Prism Launcher choose *Add Instance → Import* and pick the zip (or drag it onto the window). The CurseForge app and ATLauncher import the same zip. The mods are downloaded on the first import.
- **Server:** unzip it into an empty folder, run `install.sh` (Linux/macOS) or `install.bat` (Windows), then follow `README-SERVER.md`.

The version comes from `pack.toml`. You can also run the same steps without Nix: `python3 tools/release.py curseforge OUT` or `python3 tools/release.py server OUT`, with packwiz on your `PATH`.

### Restoring a backup

FTB Backups 2 saves the world every 30 minutes (the last 5 are kept) as zips in the `backups/` folder of the instance or server. To go back to one of them, close the game (or stop the server) and run, from that same folder:

- **Windows:** double-click `restore-backup.bat`.
- **Linux/macOS:** `./restore-backup.sh` (run `chmod +x restore-backup.sh` once if it is not executable).

The script lists the backups, newest first, checks the chosen zip against the checksum FTB Backups recorded, and restores the world. The current world is never deleted: it is renamed to `<world>.before-restore-<date>`, so you can undo by swapping the folders back. You can pass a zip directly: `./restore-backup.sh backups/2026-10-11_2-0-0.zip`.

## Development

### Repository layout

| Path | What it is |
| --- | --- |
| `pack.toml`, `index.toml`, `mods/` | The packwiz pack. One `.pw.toml` per CurseForge mod, plus the GTIACore and GTNA jars |
| `config/`, `defaultconfigs/`, `resourcepacks/` | Shipped with the pack (the quest book is generated into `config/ftbquests`) |
| `quests-src/` | Quest book sources (TOML) and processing-line flowchart data |
| `manifest/` | `full.lock.json` (mods with CurseForge ids and SHA-256), `client-only.txt`, recipe/item dumps for the quest checker |
| `tools/` | Build and QA scripts |
| `kubejs/` | Small data tweaks, not shipped yet (KubeJS isn't in the pack) |
| `docs/` | Public docs: tier plans and flowcharts |
| `.github/` | CI (package + checks), server installer, issue templates |

### Mods

`manifest/full.lock.json` is the source of truth, and `mods/` is generated from it:

```sh
python3 tools/pack.py lock          # resolve mods + required dependencies into the lock
python3 tools/pack.py fetch         # download them into the cache and check SHA-256
python3 tools/packwiz_sync.py       # write mods/*.pw.toml, copy the local jars, packwiz refresh
python3 tools/packwiz_sync.py --check
```

A mod that a dedicated server can't load goes in `manifest/client-only.txt` (`tools/server_smoke.py` lists them). GTIACore and GTNA are local builds; set `GTIA_JAR` / `GTNA_JAR` if your jars are elsewhere.

### Configs and quests

- Edit files under `config/` or `defaultconfigs/`, then run `packwiz refresh`.
- Quests: edit `quests-src/*.toml`, never the generated `.snbt`. Then run `python3 tools/questgen.py build && python3 tools/questgen.py check`.

### Other tools

```sh
python3 tools/pack.py instance                     # build a Prism instance straight from the lock (testing)
python3 tools/pack.py sync --instance NAME         # copy config/ over an existing instance
python3 tools/server_smoke.py                      # boot a dedicated server with the locked mods
python3 tools/release.py curseforge|server OUT     # build the release zips (what CI and Nix run)
python3 tools/flowchart.py                         # render processing-line flowcharts (Graphviz)
python3 tools/reach.py                             # recipe reachability / shortcut queries
```

### CI

- `check.yml` runs on every push and PR. It fails if `index.toml` is stale, the quest book wasn't rebuilt, or a quest isn't reachable.
- `package.yml` builds the client and server zips:
  - every push to `main` updates the `nightly` release;
  - running it by hand with a tag (e.g. `0.1.0-dev-1`) creates that release.

## Contributing

Playtesting feedback is the most useful thing right now. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

- Pack structure, configs, scripts, original textures and translations: **CC BY-NC-SA 4.0** ([LICENSE.txt](LICENSE.txt)).
- Quest texts: all rights reserved unless stated otherwise.
- GTIACore code: LGPL-3.0, in its own repository.
- Third-party mods keep their own licenses; see [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
