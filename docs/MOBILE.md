# Playing on Android

GregTech Infinity Ascension runs on Android phones and tablets through the **Amethyst** launcher, the same way GregTech: New Horizons does.

> **Status:** the mobile pack (`.mrpack`) is not published yet. Several mods the pack uses are only on CurseForge, and we are asking their authors for permission to include them. Testers get the build from the team. This guide is ready for when it ships.

## What you need

| | |
| --- | --- |
| **System** | Android 10 or newer |
| **Launcher** | [Amethyst](https://github.com/AngelAuraMC/Amethyst-Android/releases/latest) (free, open source) |
| **Pack** | `GregTech-Infinity-Ascension-<version>.mrpack` from the [releases page](https://github.com/GTInfinityAscension/GregTech-Infinity-Ascension/releases) |
| **Account** | A Minecraft: Java Edition account |
| **Memory** | 3 GB for singleplayer (4 GB if your phone has 8 GB or more); 2.5 GB to join a server |
| **Internet** | Wi-Fi: the first launch downloads several hundred MB |

## Install

1. **Use Wi-Fi.** Amethyst and the pack download many files the first time.
2. **Install Amethyst.** On your phone, open the [latest Amethyst release](https://github.com/AngelAuraMC/Amethyst-Android/releases/latest), download **`Amethyst.apk`** (not the Debug one) and install it. Android may ask you to allow installing apps from your browser.
3. **Download the pack.** From the [releases page](https://github.com/GTInfinityAscension/GregTech-Infinity-Ascension/releases), download the `.mrpack` of the version you want and keep it somewhere easy to find (Downloads).
4. **Add your account.** Open Amethyst and tap **+ Add account**.
5. **Import the pack.** Tap the profile selector (it shows **(Default)** and a Minecraft version), then **+ Create new profile** → **Create modpack profile** → import a zip or mrpack, and pick the `.mrpack` from step 3. Wait until the import finishes.
6. **Set the memory.** Back on the main screen, tap the settings icon (top right) → **Java tweaks**, and set the memory from the table above.
7. **Pick the profile.** Tap the profile selector again and choose **GregTech Infinity Ascension** with the version you installed.
8. **Play.** The first launch takes several minutes. The screen may stay black for a few seconds before the loading screen appears; that is normal.

## Tips

- Close other apps before playing; the pack needs most of the phone's memory.
- If the game closes while loading, lower the memory by 0.5 GB (Android may be killing it) or raise it if the log mentions `OutOfMemoryError`.
- Keep the pack's default settings. Only the official `.mrpack` with its own configs is supported on mobile.
- Joining a dedicated server needs less memory than singleplayer, because the phone does not run the world.

## Reporting a problem

Open a [mobile bug report](https://github.com/GTInfinityAscension/GregTech-Infinity-Ascension/issues/new?template=mobile_bug.yml) with your phone model, Android version, the memory you gave the game, the pack version and the log (Amethyst → the profile → **Logs**).
