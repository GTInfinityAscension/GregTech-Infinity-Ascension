# GTIA — Start, Steam and LV: what we want and what's planned

Status tags used here:

- **done** = in the game and checked in-game by me
- **built, untested** = implemented and passing automated checks, but nobody has played it yet
- **planned** = decided, not built yet

## The big picture (applies to every tier)

- **Factory first.** Satisfactory-style megafactories, real chemistry, long production lines. Grind gets solved by building more factory, never by clicking more.
- **Line length grows with tier:** Steam lines are 2–3 steps, LV/MV 4–6, HV/EV 6–10, IV+ 10+.
- **Real industrial chemistry, no PhD needed.** Recognizable processes (wood distillation, lime kiln, chlor-alkali, Bayer, Haber-Bosch...). Important molecules get two routes: an early, expensive one and a later, efficient one.
- **No ULV era.** The campaign goes Start → Steam → LV → MV... ULV still exists as a voltage label, but you don't play in it.
- **GTNA is core, not an add-on.** Large Steam machines, wireless, Flux Matrix and Component Assembler are part of the main path.
- **No research tree.** We tried one and dropped it. It felt like a worse copy of GTO.
- **Quest book is the main guide.** It's vertical and laid out like a snake (GTO/GTNH style), one chapter per tier. The tone is funny and irreverent like GTO, with Moni-style explanations. English first, then PT-BR.
- **Every quest must be doable at that point.** `questgen check` reads the pack's real recipes and flags impossible tasks, rewards you can't reach yet and machines handed out for free.
- **Modes.** Normal/Journey (later Expert) are picked when you create the world and locked, like GTO Rules.

## Start — **done**

- 29 quests, written by me and finished/polished in English. Tested in-game.
- Basic survival → tools → Wrench → Coke Oven → real Bronze and Coke, which unlocks Steam.
- Planned starter kit: basic tools, a terminal and a prospector.

## Steam — **built, untested** (42 quests)

**What we want:** a recognizable GregTech Steam age with no EU. The new parts are the GTNA Large Steam multiblocks and the first real-chemistry machines.

Main path (snake layout):

1. Boilers → Macerator in the spine → steel.
2. Then it splits into **two tracks that must both be finished to leave Steam**:
   - **First circuit:** molds, Vacuum Tube, Resistor, Resin Circuit Board, Red Alloy cable. Uses GTL-style Resin boards; no GTO vacuum-tube chain.
   - **LV hull:** LV casing, tin cable, wrought iron plates.
3. Rubber: Sticky Resin in the centrifuge gives 3 Raw Rubber + 100 mB Glue, then Raw Rubber + Sulfur gives Rubber.

Side content:

- **GTNA multiblocks panel:** Large versions in three families (ore, forming, heat), plus Precision, Hydraulic, Breel and Cactus Wonder. The Large Steam Circuit Assembler lets you mass-produce circuits but never blocks LV.
- **Wireless steam** (GTNA) is available from Steam.
- **Chemistry slice 01** : Wood Retort and Lime Kiln, both primitive multiblocks built on the Coke Oven, plus flux steel in the PBF. Their byproducts sit in tanks until LV can use them.
- **Our own material:** Phase Matrix ore (Y 40–60) → crushed → impure dust → + iron in the Steam Alloy Smelter = **Pulsating Alloy**. Red Alloy + Pulsating = **Conductive Alloy** (a zero-loss 4 A wire). This one is **done**.

To leave Steam you need Steel, Rubber, the first circuit, cables, power and your first electric machine. Doing all the Steam infrastructure is encouraged but not mandatory.

## LV — **built, untested** (61 quests, v2)

**What we want:** every quest leads somewhere. No dead ends: each line ends at something that actually uses it.

Main path:

1. **Power:** LV Steam Turbine first. Combustion, Gas and Semifluid are alternatives. Generator Array comes at the end of LV.
2. **Motors → components → build lines:**
   - Bender → Wiremill → Extractor
   - Mixer → Centrifuge → Electrolyzer → Chemical Reactor → Fluid Heater
   - Assembler is on the main line
3. **Chlor-alkali:** a Diaphragm Cell (an asbestos diaphragm that wears out) and brine separation in the centrifuge, with the salt going back to the Mixer.
4. **Wood line to a real use:**
   - Methyl Acetate + Vinyl Acetate → PVA → Glue in bulk
   - Creosote → Brewery → Lubricant for the Cutter
5. **Plastic:** ethanol (fermentation) → LV Catalytic Dehydrator → ethylene → Polyethylene, all inside LV at 30 EU/t. PE does **not** block the first circuit.
6. **EBF:** 16 Cupronickel coils plus two LV energy hatches reach MV voltage, and the first product is **Aluminium**. That's the LV → MV gate.
7. **Exit:** Good Electronic Circuit + MV hull.

Also in LV:

- **AE2:** storage and terminal in LV; autocrafting waits for MV.
- **Nexus Flux Matrix** (wireless EU with 5% loss) arrives late in LV, after Aluminium.
- **Component Assembler** (GTNA) arrives late in LV. Normal LV component recipes stay available for bootstrapping.
- Annealed Copper (Arc Furnace) improves components but doesn't block the EBF.

## Where a second person helps most

- **Play Start → Steam → LV** and write down where it's slow, confusing, broken, or where a quest doesn't tell you what to do next.
- Check quest text and tone, and later help with PT-BR.
- Spot recipe shortcuts and circular recipes.
- Weigh in on the MV chemistry (Bayer, Hall-Héroult, Contact, Haber-Bosch, Solvay). It's already built but hasn't been reviewed in-game.
