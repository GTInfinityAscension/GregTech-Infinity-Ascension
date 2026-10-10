# Contributing to GTIA

Thanks for helping! The pack is in early development, so the most useful things right now are:

1. **Playtesting Start → Steam → LV.** Play from a fresh world and note where it's slow or confusing, or where a quest doesn't tell you what to do next.
2. **Finding broken progression:** impossible recipes, circular recipes, recipes that skip a tier, rewards that make a later quest pointless.
3. **Quest text:** tone, typos, clearer explanations. English is the main language. PT-BR and ZH come later.

## Reporting a problem

Open an issue with:

- the pack version (or the commit you built from)
- where you are in the progression (chapter + quest)
- what you did, what you expected and what happened
- screenshots of the recipe/GUI/quest, and `latest.log` if something crashed

## Working on the pack

- **Quests:** edit `quests-src/*.toml`, never the generated `config/ftbquests/quests/chapters/*.snbt`. Then run:
  ```sh
  python3 tools/questgen.py build && python3 tools/questgen.py check
  ```
  `check` must pass with no errors before a PR.
- **Mods:** don't add jars. Propose the mod in an issue first; if it's accepted, it gets added to the lock with `tools/pack.py lock`.
- **Machines and recipes** live in Java (GTIACore and GTNA). KubeJS is only for small tweaks.
- **Art:** don't replace existing textures. Propose new ones in an issue.

## Design rules

Before proposing content, please keep these in mind:

- Grind gets solved with more factory, never more clicking.
- Production lines get longer each tier.
- Use real chemistry where possible.
- There's no ULV era and no research tree.
- Every quest must be reachable at the point where it appears.

The [roadmap](ROADMAP.md) and [Start/Steam/LV plan](docs/START_STEAM_LV_PLAN.md) explain where things are going.
