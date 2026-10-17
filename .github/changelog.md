## Changes in 0.1.0-dev-4

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
