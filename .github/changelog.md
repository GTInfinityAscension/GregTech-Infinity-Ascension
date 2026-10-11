## Changes in this build

### New
- **Crafting Chain** replaces Fabricate. Press **Ctrl+D** or **Ctrl+click** an item or favorite in EMI (or JEI) to craft it together with every intermediate crafting step, like the crafting chain of GTNH's NEI. Hold **Shift** for a full stack. EMI favorites that carry a recipe are crafted with that recipe and are used first for the intermediate items. While a **Crafting Station** is open, the containers on its five sides are used too. Enchanted items are never spent, and when something is missing the chat lists every missing base item.
- **More GTIA Rules** (44 in all, in seven groups): recipe EU/t, casings per craft, every GregTech "hard recipe" option (wood, iron, redstone, glass, paper, charcoal, circuits, controllers…), small and large boiler steam, fuel efficiency, maintenance, cleanroom, explosions, active transformers, assembly line order, miner speed, electric tool energy and wear, prospector energy, enchanted GregTech tools, ore vein spacing, Electric Void Miner duration, Ultimine limit and keep inventory. Rules marked **[restart]** are read when the game starts: a world that uses different values saves them and asks for a restart.
- **`/gtia rules`** opens the read-only rules of the world you are in.
- **GTNA 0.5.5**: fixes the launch crash with JEI 15.32 and newer.

### Changes
- The **GTIA Rules button is gone from the pause menu**; use `/gtia rules`.
- **Xaero's Minimap** sits in the top-right corner on new installs.
- **Fuels are no longer worth less energy in faster presets**: the recipe duration rule skips generator and boiler fuels, which follow the new fuel efficiency rule.
- Journey now also makes recipes cheaper, turns off maintenance and the stricter vanilla recipes, makes 3 casings per craft and keeps your inventory on death.
