# GTIA dedicated server

1. Install Java 17 or newer.
2. Run `./install.sh` (Linux/macOS) or `install.bat` (Windows) in this folder. It:
   - downloads the Forge installer and installs the server (the hash is checked),
   - downloads packwiz-installer and fetches every server-side mod of this release from CurseForge.
3. Set `eula=true` in `eula.txt`, then start with `./run.sh` / `run.bat`. Memory goes in `user_jvm_args.txt` (8 GB or more recommended).

GTIACore and GTNA are already in `mods/`. Client-only mods (Oculus, FastQuit, Nolijium) are not installed.
To update, replace this folder's `config/`, `defaultconfigs/`, `mods/gtia-*.jar`, `mods/gtna-*.jar` and `gtia-installer/` with the new release, then run the installer again. Back up `world/` first.
