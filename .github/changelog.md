## Changes in this build

### New
- **GTIA Rules on world creation.** The *Game* tab of the Create World screen has a **GTIA Rules** button: pick Journey, Normal or Custom, search the rules, read what each one does and the value of every preset, and edit the values in Custom. Recipes are regenerated for the chosen preset before the world is created. In a running world, the pause menu shows the rules read-only.
- **Crafting Station** (GTIACore): a crafting table that shows up to five containers touching it (the four sides and below), chests, double chests and modded storage alike. Switch between them with the tabs, shift-click items in and out, and EMI's recipe fill pulls ingredients from them too. Recipe: Crafting Table + any wooden chest.
- **Fabricate**: click an item in EMI to hand-craft it and every intermediate step from your inventory, like the crafting helper of GTNH's NEI.
- **Discord Rich Presence** (CraftPresence): shows that you are playing GregTech Infinity Ascension, the dimension you are in, singleplayer or server, and the main menu.
- **CozyUI+** resource pack, enabled by default for new installs, and **Complementary Reimagined** shaders included (this also fixes the `_0EuphoriaPatches_ErrorShader` entry).
- **ModernSpace 0.3.1** imports the personal dimensions of worlds made with GTNA 0.5.2 or older; **GTNA 0.5.4** is the published release (its pt_br translation is now complete).
- **Translations**: the whole quest book in Portuguese (pt_br) and Simplified Chinese (zh_cn); GTNA, GTIACore, ModernSpace and ModernManipulator in Simplified Chinese and Brazilian Portuguese.

### Changes
- **Start**: the welcome reward is now a Vanadium Steel Axe, Pickaxe and Shovel (about twice the durability of the Fluix tools it replaces). *Room for a Factory* gives the Personal Space portal again.
- **The research tree is gone from the pack**: its Start quest is removed and GTNA's research tree (K key, screen and commands) is turned off.
- **GTNA multiblock previews** (EMI/JEI and structure GUIs) build very large structures in batches off the main thread, so the Eye of Harmony and Forge of the Gods previews no longer stall or fail.
- **Performance**: spark's always-on background profiler is off, Chloride client settings tuned like GregTech Odyssey, sky colour recomputed less often. Java 21 is now the recommended runtime (see the README).
- Releases: only the newest beta and the newest dev/pre/alpha are kept; every change to `main` is still built as a CI artifact.
