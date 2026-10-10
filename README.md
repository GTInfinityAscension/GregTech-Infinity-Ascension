# GregTech Infinity Ascension (GTIA)

A GregTech modpack for Minecraft 1.20.1 built on **GTCEu Modern**, **[GregTech Nexus Addon (GTNA)](https://github.com/Raishxn/GregTech-Nexus-Addon)** and **[GTIACore](https://github.com/Raishxn/GTIACore)**.

GTIA is guided GregTech where the factory is the star: Satisfactory-style megafactories, real industrial chemistry and long production lines. You start in Steam, go electric, head to space and keep scaling. Large machines, wireless power and AE2 are part of the main path, not side content. The quest book is the main guide, and it's written with a sense of humour.

> **Status: early development.** No playable release yet. Start → Steam → LV is the first slice we want people to play; see the [roadmap](ROADMAP.md) and the [Start/Steam/LV plan](docs/START_STEAM_LV_PLAN.md).

## Design pillars

- **Grind is solved with more factory**, never with more clicking.
- **Lines get longer every tier:** Steam 2–3 steps, LV/MV 4–6, HV/EV 6–10, IV+ 10+.
- **Real chemistry, no PhD:** wood distillation, lime kiln, chlor-alkali, Bayer + Hall-Héroult, Contact process, Haber-Bosch, Solvay... Important molecules have an early, expensive route and a later, efficient one.
- **No ULV era and no research tree.** The campaign goes Start → Steam → LV → MV → HV → ...
- **Every quest is reachable.** A checker reads the pack's real recipes and fails the build if a quest asks for something you can't make yet.
- **Modes:** Normal/Journey are picked at world creation and locked.

## Repository layout

| Path | What it is |
| --- | --- |
| `config/` | Pack configs, including the generated FTB Quests book |
| `kubejs/` | Small data tweaks (most content is Java, in GTIACore/GTNA) |
| `resourcepacks/` | GTIA's own resource packs |
| `quests-src/` | Quest book sources (TOML) and processing-line flowchart data |
| `manifest/` | Mod lockfiles with sources and SHA-256 (`full.lock.json`, `first-slice.lock.json`) |
| `tools/` | Build and QA scripts (below) |
| `docs/` | Public docs: tier plans and flowcharts |

## Tools

```sh
python3 tools/pack.py lock|fetch|verify|instance   # lock mods, download, check hashes, build a Prism instance
python3 tools/pack.py --profile first-slice instance   # smaller test instance
python3 tools/questgen.py build                      # generate the quest book from quests-src/
python3 tools/questgen.py check                      # reachability check: can the player do this quest here?
python3 tools/flowchart.py                           # render processing-line flowcharts (Graphviz)
python3 tools/server_smoke.py                        # boot a dedicated server with the locked mods
python3 tools/reach.py                               # recipe reachability / shortcut queries
```

GTIACore and GTNA are local builds for now. Set `GTIA_JAR` and `GTNA_JAR` if your jars are elsewhere.

## Contributing

Playtesting feedback is the most useful thing right now. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

- Pack structure, configs, scripts, original textures and translations: **CC BY-NC-SA 4.0** ([LICENSE.txt](LICENSE.txt)).
- Quest texts: all rights reserved unless stated otherwise.
- GTIACore code: LGPL-3.0, in its own repository.
- Third-party mods keep their own licenses; see [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).
