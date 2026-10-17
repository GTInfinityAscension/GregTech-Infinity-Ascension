# Playing on Android

GregTech Infinity Ascension runs on Android phones and tablets through the **Amethyst** launcher, the same way GregTech: New Horizons does.

> **Status:** the mobile pack (`.mrpack`) ships with every release from 0.1.0-dev-4 on. Mods that are only on CurseForge are included inside it; if a mod's author asks us to remove theirs, we will at once.

## What you need

| | |
| --- | --- |
| **System** | Android 10 or newer |
| **Launcher** | [Amethyst](https://github.com/AngelAuraMC/Amethyst-Android/releases/latest) (free, open source) |
| **Pack** | `GregTech-Infinity-Ascension-<version>.mrpack` from the [releases page](https://github.com/GTInfinityAscension/GregTech-Infinity-Ascension/releases) |
| **Account** | A Minecraft: Java Edition account |
| **Memory** | **2.5 GB** on an 8 GB phone, **3 GB** on 12 GB or more (not more: see Tips). Joining a server needs about 0.5 GB less |
| **Internet** | Wi-Fi: the first launch downloads several hundred MB |

## Install

1. **Use Wi-Fi.** Amethyst and the pack download many files the first time.
2. **Install Amethyst.** On your phone, open the [latest Amethyst release](https://github.com/AngelAuraMC/Amethyst-Android/releases/latest), download **`Amethyst.apk`** (not the Debug one) and install it. Android may ask you to allow installing apps from your browser.
3. **Download the pack.** From the [releases page](https://github.com/GTInfinityAscension/GregTech-Infinity-Ascension/releases), download the `.mrpack` of the version you want and keep it somewhere easy to find (Downloads).
4. **Install Forge.** In Amethyst, install **Forge 1.20.1 – 47.4.23** from its version/mod loader installer and wait for it to finish. Forge prepares some game files on the phone; without this step the game stops at once with `Invalid paths argument, contained no existing paths`.
5. **Add your account.** Open Amethyst and tap **+ Add account**.
6. **Import the pack.** Tap the profile selector (it shows **(Default)** and a Minecraft version), then **+ Create new profile** → **Create modpack profile** → import a zip or mrpack, and pick the `.mrpack` from step 3. Wait until the import finishes.
7. **Set the memory.** Back on the main screen, tap the settings icon (top right) → **Java tweaks**, and set the memory from the table above.
8. **Pick the profile.** Tap the profile selector again and choose **GregTech Infinity Ascension** with the version you installed.
9. **Play.** The first launch takes several minutes. The screen may stay black for a few seconds before the loading screen appears; that is normal.

## Tips

- Close other apps before playing; the pack needs most of the phone's memory.
- **If the launcher closes by itself** (often while creating a world), Android killed it for using too much memory: lower the memory by 0.5 GB. The game uses about 2–2.5 GB on top of the value you set (graphics, textures, code), so giving it more makes this worse. Raise it only if the log says `OutOfMemoryError`.
- Loading and world creation are slower than on a PC (several minutes the first time); that is expected.
- Keep the pack's default settings. Only the official `.mrpack` with its own configs is supported on mobile.
- Joining a dedicated server needs less memory than singleplayer, because the phone does not run the world.

## Reporting a problem

Open a [mobile bug report](https://github.com/GTInfinityAscension/GregTech-Infinity-Ascension/issues/new?template=mobile_bug.yml) with your phone model, Android version, the memory you gave the game, the pack version and the log (Amethyst → the profile → **Logs**).
