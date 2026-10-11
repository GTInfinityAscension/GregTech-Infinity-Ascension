# Manifest

| File | What it is |
| --- | --- |
| `full.lock.json` | The whole pack: 127 jars, each with SHA-256 and (for remote mods) its CurseForge project/file ID. Built by `tools/pack.py lock` from the audited source list minus `full.exclude`. |
| `first-slice.lock.json` | A 16-jar subset for quick Start → Steam → LV tests, built from `first-slice.seeds` plus the required dependencies. |
| `full.exclude` | Mods left out of the full pack, with the reason. |
| `source-audit-2026-09-29.tsv` | Where each jar comes from (download source and hash). `pack.py` reads it. |
| `registry/` | Item, fluid, machine and recipe dumps that `questgen.py check` uses to prove quests are reachable. See its README. |

GTIACore (`gtia`), GTNA (`gtna`) and, until it is on CurseForge, ModernSpace (`modernspace`) are local builds, so their hashes change every time they're recompiled. Run `python3 tools/pack.py lock` after rebuilding them.
