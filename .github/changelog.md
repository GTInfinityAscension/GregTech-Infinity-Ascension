## Changes in 0.1.0-dev-6

### New
- **Welcome** and a new **Start**: the first chapter now covers reading the book, your world's mode, the rules, the community, EMI, Crafting Chain and maps; the Start is a step-by-step road from your first log to your first Coke, with tips next to the steps that need them (Ultimine, ore veins, GregTech tools, fluids, your first multiblock, boilers).
- **Multiblock Goals**: every multiblock in the pack (254) as a goal, in columns by family and rows by tier, with each mod's own description.
- **Tips** in the LV, MV and HV chapters: voltage and amperage, cable loss, covers, programmed circuits, coil temperature, overclocking, maintenance, batch mode, the Cleanroom, distillation, catalyst wear and organs before the Moon.
- The Steam supplies at the end of Start are per-mode kits: Normal worlds get 16 Coke Blocks, 16 Bronze Ingots and a Steel Mining Hammer.
- **Agriculture** and **Bees** chapters in the Systems group: Agronomica crops from the first crop sticks to the MV Greenhouse, and the HV bee line from the first cage to comb leaching and the Mutation Chamber.
- **Era banners** at the top of Start, Steam, LV, MV, HV, Agriculture and Bees.
- **Multiblock Goals rewards**: each goal gives a small pack of its row's metal (bronze, steel, aluminium, stainless steel, titanium, tungstensteel and up).
- **Chapter backgrounds**: each chapter has its own pixel-art background in its era's colour (Steam bronze, LV grey, MV blue, HV light steel) or its theme (stone, farmland, honeycomb, coils, circuits).
- A **Journey World** / **Normal World** quest at the start of the book says what your world's mode changes; the mode's Starting Kits are visible from the first minute.

### Changes
- **One route per base chemical**: GTCEu and GTNA shortcuts that skipped GTIA's chemistry plants are gone in both modes (aluminium from bauxite/sapphire/clay electrolysis, sulfuric acid, ammonia, nitric acid, chlor-alkali without the Diaphragm Cell, soda ash, titanium tetrachloride and titanium outside the Kroll Reactor, quicklime, ethylene from ethanol or glycerol, log pyrolysis). By-products of ores, distillation and recycling stay, and so does ethylene from cracking. The quests for nitric acid, ammonia, titanium, vinyl acetate and polyethylene now point to the GTIA plants.
- **Steam, LV, MV and HV follow the GTNH 2.9 chapter layout**: quests sit where their GTNH counterpart is, with GTIA-only quests next to the quest they come from. Multiblock renders are gone from the map and the text (press R for the EMI preview).
- **Quest book layout** redone in the GTNH way: chapters read left to right in dependency columns, small quests sit around the quest they come from, collections form tidy blocks, and lines that would cross the chapter are hidden. Steam went from 102 crossing lines to 5. Darker book background and thick red/green lines.
- **Creating a world** with a preset that changes startup rules (Journey, or a Custom one) now asks you to **Save and Quit** first, like GTO's difficulty; when you start the game again the create-world screen keeps your choice. Opening a saved world that needs other startup values asks too.
- The **Rocket Assembler** and **Greenhouse** controllers face out of their structures; their tooltips follow the GTIA layout.
- New Discord invite: https://discord.gg/TW5vugknk5

### Fixes
- **EMI multiblock previews** no longer draw over each other (one multiblock per page again; Ascension Optimizer 0.2.1).
- The empty **Bee Cage**, the **Honey Treat** and the **Greenhouse** controller had no recipe.

## Changes in 0.1.0-dev-5

Start → HV is now playable end to end: every quest asks for something you can make with what the quests before it unlock, including the five Moon quests.

### New
- **Organs** (ported from GregTech Odyssey 0.6). Right click the **Organ Modifier**: each organ slot sits on its place in a body outline, the eight wing slots on the right, and a readout shows what your set gives. Organs come from the Assembler in four tiers (MV, EV, LuV, UV parts). Your lowest organ is your **organ set tier**: armor and toughness, leg speed, extra reach, a liver that cures poison and wither, lungs that breathe under water, no hunger at tier 3 and flight at tier 4. **Steel**, **Fairy** and **Mechanical** wings fly until they wear out or run out of charge. On Normal, the Moon and Mars hurt a body below organ set tier 1.
- **New chemistry plants**, with real stoichiometry and closed loops:
  - **Ostwald Converter** (MV): ammonia → nitric oxide → nitrogen dioxide → nitric acid over a cobalt oxide gauze; the Moon's platinum gives a faster gauze.
  - **Claus Unit** (HV): hydrogen sulfide from oil desulfurization becomes sulfur over Bayer alumina.
  - **Kroll Reactor** (HV): the Moon's ilmenite (or rutile) to titanium tetrachloride, then titanium with magnesium under argon.
  - **Siemens Reactor** (HV): silicon → trichlorosilane → polysilicon; 16 polysilicon grow a silicon boule in the EBF.
- **GTIA Rules: 54 rules.** Eight match GTO Rules: rubber tree chance, infinite bedrock fluids, require GregTech tools, material hazards, extra regeneration (food threshold and strength), planets need organs, organ cost. Two are GTIA's own, for the chemistry plants: **catalyst wear** (Normal: a catalyst has a 1% chance to wear out per run, so it becomes a supply line; Journey: never) and **heat recovery** (Journey: 1.5× the steam the plants make from their reaction heat).
- **New main menu**: animated space-factory background, animated GT:IA logo, four buttons in a row and a Discord button. The game window shows the pack name and icon.
- **Highlight images** in the quest book: isometric pictures of 19 multiblocks, from the Wood Retort to the Rocket Assembler.
- Quests for the organs, the four new plants and polysilicon.

### Changes
- The **Moon quest** now asks you to reach the Moon; the lunar ore quests are no longer marked as pending.
- The **Large Steel Boiler** quest sits at the end of MV (it needs four HV circuits).
- **PackMenu** is replaced by **FancyMenu** (with Konkrete and Melody).
- The Rocket Assembler quest describes the real multiblock.
