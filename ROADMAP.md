# Roadmap — GregTech Infinity Ascension

Last updated: **2026-10-17**. No release dates; items are in priority order.

What the boxes mean:

- **[x] done** = in the game and checked in-game
- **built, untested** = implemented and passes the automated checks (GameTests, quest reachability, server boot), but nobody has played it yet
- **[ ] planned** = decided, not built yet

The full roadmap (MV → HV → space → EV+) exists as a guide. We only polish a tier after the previous one has been played.

## Foundation

- [x] GTIACore as its own mod, with GTNA required on client and server. 18 GameTests.
- [x] Phase Matrix ore and the Steam route to Pulsating and Conductive Alloy, approved in-game.
- [x] Reproducible pack: 109 mods locked with SHA-256 (`manifest/full.lock.json`). `tools/pack.py` builds a clean instance and `tools/server_smoke.py` boots a server with it.
- [x] Quest tooling: `questgen.py` generates the book and `check` fails if a quest or reward isn't reachable at that point.
- [x] Start chapter (29 quests), tested in-game.

## Stage 1 — first playable slice: Start → Steam → LV

**Goal:** a fresh world can reach Aluminium in the EBF with no given items, impossible recipes or later-tier dependencies.

- [x] **GTIA-01 · Reproducible base.** The lockfile and clean instance are done. Still to do: a client test of the full instance.
- [ ] **GTIA-02 · Steam chapter:** built, untested (42 quests). The two exit tracks are the first circuit and the LV hull. The GTNA Large Steam panel is in it, plus the Wood Retort and Lime Kiln.
- [ ] **GTIA-03 · First circuit:** built, untested. Resin boards, Vacuum Tube and Resistor, made by hand. The Large Steam Circuit Assembler is an upgrade and never blocks LV.
- [ ] **GTIA-04 · LV chapter:** built, untested (61 quests, v2). It goes turbine → motors → build lines → chlor-alkali → wood line → plastic → EBF → Aluminium, and exits at Good Electronic Circuit + MV hull.
- [ ] **GTIA-05 · Survival playthrough:** play the whole slice on a clean instance, write down the bottlenecks and fix them.
- [ ] **GTIA-06 · Real multiblock structures** for the Wood Retort, Lime Kiln and Diaphragm Cell (current ones are placeholders).
- [ ] **GTIA-07 · Quest polish:** the reward economy (pack currency + shop), tier title art and tone pass.

## Stage 2 — LV → MV → HV

- [ ] **GTIA-08 · MV chapter:** built, untested (75 quests, v7). Covers gems and laser engraving, silicon and chips, stainless steel and Kanthal (cooled in the Chemical Bath). Exits at Advanced Integrated Circuit + HV hull.
- [ ] **GTIA-09 · MV chemistry:** built, untested. Bayer Digester, Hall-Héroult Cell, Contact Converter, Ammonia Converter and Solvay Tower, which run alongside the GTCEu routes as the efficient alternative.
- [ ] **GTIA-10 · GTNA infrastructure by tier.** Flux Matrix arrives at the end of LV with 5% loss. The Component Assembler arrives at the end of LV, and the Universal Factory in mid MV.
- [ ] **GTIA-11 · AE2:** storage at the end of LV, autocrafting in MV. We also need to audit AE2 recipes that could skip progression.
- [ ] **GTIA-12 · HV chapter:** built, untested (109 quests, v6): distillation, cracking, plastics, the Cleanroom, the circuit ladder up to the EV circuit, the Rocket Assembler and the Moon.
- [ ] **GTIA-20 · MV/HV chemistry 2:** built, untested. Ostwald Converter (MV), Claus Unit, Kroll Reactor and Siemens Reactor (HV).
- [ ] **GTIA-21 · Organs** (from GTO 0.6): built, untested. Organ Modifier, four organ tiers, three wings; Moon and Mars need an organ set on Normal.

## Stage 3 — space and EV/IV

- [ ] **GTIA-13 · Space:** the Moon in HV (built, untested),  Mars and Venus/Mercury in EV. Few destinations, each with its own identity.
- [ ] **GTIA-14 · Void mining:** an electric EV Void Miner (GTNA) as the backbone of passive mining, unlocked per planet.
- [ ] **GTIA-15 · Discovered fluids:** prospect, extract and then produce remotely. The Martian Radon prototype is ready.
- [ ] **GTIA-16 · Zero-gravity production** and the later stages.

## Stage 4 — scale and public test

- [ ] **GTIA-17 · IV+ progression**, Draconium, and the late-game chemistry upgrades (rotary kiln, membrane cell...).
- [ ] **GTIA-18 · Performance and multiplayer:** big factories, reloads, dedicated servers.
- [ ] **GTIA-19 · Public test build.** It needs to be playable through HV, with install instructions, credits, a changelog and known issues. Free on CurseForge and Modrinth.

## Later / studying

- [x] Journey and Normal presets with 52 GTIA Rules and mode-only quests (Expert postponed).
- [ ] PT-BR and ZH translations (English first).
- [ ] Migrating mod management to packwiz, GTO-style, before the first release.

## Reporting problems

Tell us the pack version, where you are in the progression, what you did, and what you expected vs. what happened. Screenshots of recipes and GUIs help a lot.
