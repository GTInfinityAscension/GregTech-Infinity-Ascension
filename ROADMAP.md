# Roadmap — GregTech Infinity Ascension

Last updated: **2026-10-21**. No release dates; items are in priority order.

What the boxes mean:

- **[x] done** = in the game and checked in-game
- **built, untested** = implemented and passes the automated checks (GameTests, quest reachability, server boot), but nobody has played it yet
- **[ ] planned** = decided, not built yet

The full roadmap (MV → HV → space → EV+) exists as a guide. We only polish a tier after the previous one has been played.

## Foundation

- [x] GTIACore as its own mod, with GTNA required on client and server, checked by GameTests.
- [x] Phase Matrix ore and the Steam route to Pulsating and Conductive Alloy, approved in-game.
- [x] Reproducible pack: 138 mods locked with SHA-256 (`manifest/full.lock.json`). `tools/pack.py` builds a clean instance and `tools/server_smoke.py` boots a server with it.
- [x] Quest tooling: `questgen.py` generates the book and `check` fails if a quest or reward isn't reachable at that point.
- [x] Start chapter (29 quests), tested in-game.

## Stage 1 — first playable slice: Start → MV

**Next release target:** Start → MV played and fixed, with MV AE2 (D-333). Megastructures are frozen until HV has been played.

**Goal:** a fresh world can reach Aluminium in the EBF with no given items, impossible recipes or later-tier dependencies.

- [x] **GTIA-01 · Reproducible base.** The lockfile and clean instance are done. Still to do: a client test of the full instance.
- [ ] **GTIA-02 · Steam chapter:** built, untested (42 quests). The two exit tracks are the first circuit and the LV hull. The GTNA Large Steam panel is in it, plus wood and lime chemistry in the Coke Oven.
- [ ] **GTIA-03 · First circuit:** built, untested. Resin boards, Vacuum Tube and Resistor, made by hand. The Large Steam Circuit Assembler is an upgrade and never blocks LV.
- [ ] **GTIA-04 · LV chapter:** built, untested (61 quests, v2). It goes turbine → motors → build lines → chlor-alkali (Electrolyzer) → wood line (Distillery) → plastic → EBF → Aluminium, and exits at Good Electronic Circuit + MV hull.
- [ ] **GTIA-05 · Survival playthrough:** play the whole slice on a clean instance, write down the bottlenecks and fix them.
- [x] **GTIA-06 · No custom chemistry multiblocks up to HV.** The real chemistry runs as recipes in GTCEu and GTNA machines (D-335).
- [ ] **GTIA-22 · Easy start:** a Fortune pickaxe in the starting kit that works on GregTech ores, FTB Ultimine from the start, the personal dimension in Steam, wireless steam only in Journey.
- [ ] **GTIA-07 · Quest polish:** the reward economy (pack currency + shop), tier title art and tone pass.

## Stage 2 — LV → MV → HV

- [ ] **GTIA-08 · MV chapter:** built, untested (75 quests, v7). Covers gems and laser engraving, silicon and chips, stainless steel and Kanthal (cooled in the Chemical Bath). Exits at Advanced Integrated Circuit + HV hull.
- [ ] **GTIA-09 · MV chemistry:** built, untested. Bayer, Hall-Héroult (EBF), Contact, Haber-Bosch and Solvay as recipes in the Chemical Reactor and the EBF.
- [ ] **GTIA-10 · GTNA infrastructure by tier.** Flux Matrix wireless energy arrives in HV with losses, full wireless in EV. The Component Assembler arrives at the end of LV, and the Universal Factory in mid MV.
- [ ] **GTIA-11 · AE2:** storage and first automation in MV, refinement (ExtendedAE Assembler Matrix) in HV. We also need to audit AE2 recipes that could skip progression.
- [ ] **GTIA-12 · HV chapter:** built, untested (109 quests, v6): distillation, cracking, plastics, the Cleanroom, the circuit ladder up to the EV circuit, the Rocket Assembler and the Moon.
- [ ] **GTIA-20 · MV/HV chemistry 2:** built, untested. Ostwald (MV), Claus, Kroll and Siemens (HV) as Chemical Reactor recipes.
- [ ] **GTIA-21 · Organs** (from GTO 0.6): built, untested. Organ Modifier, four organ tiers, three wings; an optional bonus, never a gate.

## Stage 3 — space and EV/IV

- [ ] **GTIA-13 · Space:** the Moon in HV (built, untested), Mars and Venus/Mercury in EV on Ad Astra planets; GTIA's own planets from IV. Visit each destination once, then automate it by data.
- [ ] **GTIA-14 · Void mining:** an electric EV Void Miner (GTNA) as the backbone of passive mining, unlocked per planet.
- [ ] **GTIA-15 · Discovered fluids:** prospect, extract and then produce remotely. The Martian Radon prototype is ready.
- [ ] **GTIA-16 · Zero-gravity production:** required in EV, in space or in a Cleanroom-like ground simulator.
- [ ] **GTIA-23 · EV power:** fission, nitrobenzene and high-octane fuels, Large Gas Turbine on refinery gas.

## Stage 4 — scale and public test

- [ ] **GTIA-17 · IV+ progression** and Mega versions of the chemistry plants (rotary kiln, membrane cell...).
- [ ] **GTIA-18 · Performance and multiplayer:** big factories, reloads, dedicated servers.
- [ ] **GTIA-19 · Public test build.** It needs to be playable through HV, with install instructions, credits, a changelog and known issues. Free on CurseForge and Modrinth.

## Later / studying

- [x] Journey and Normal presets with 52 GTIA Rules and mode-only quests (Expert postponed).
- [ ] PT-BR and ZH translations (English first).
- [ ] Migrating mod management to packwiz, GTO-style, before the first release.

## Reporting problems

Tell us the pack version, where you are in the progression, what you did, and what you expected vs. what happened. Screenshots of recipes and GUIs help a lot.
