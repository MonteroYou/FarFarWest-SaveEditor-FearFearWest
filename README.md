# Far Far West Save Editor — Frost & Cactus Magic Fix

A save editor for **Far Far West**, updated for the **Fear Fear West** game update.

## v10 — Fear Fear West compatibility fix

Earlier versions could produce saves that the game marked as corrupt, causing it to restore an automatic backup instead of loading the changes.

The issue was an outdated **CRC32 checksum** in the save's `FFWT` footer. v10 recalculates that checksum when saving and validates it when opening a file.

**I've tested v10 in-game and confirmed that edited saves load properly.**

## Features

- Edit gold and other values available in the editor.
- Edit Frost and Cactus magic levels using the existing `itemIce` and `itemCactus` XP records.
- Preserve the save structure without adding fake inventory records.
- Validate the `FFWT` checksum and verify edited output.
- Create a backup before replacing an existing save.

> **Frost and Cactus:** Level each magic naturally in-game at least once before editing it. The game must create the corresponding XP record first.

## Download and installation

1. Open the [Releases page](https://github.com/MonteroYou/FarFarWest-SaveEditor-FearFearWest/releases/latest).
2. Download **`FarFarWest_SaveEditor_v10_FearFearWest_FIXED.zip`** from the latest release.
3. Extract the entire ZIP to a folder.
4. Close Far Far West completely.
5. Double-click **`run_editor.bat`**.
6. Click **Open**, select your save, make your changes, and click **Save**.
7. Start the game and check the changes.

**Requirements:** Windows and Python 3. The launcher attempts to install `pycryptodome` if it's missing.

## Save location

On Windows, saves are normally stored in:

```text
%LOCALAPPDATA%\FarFarWest\Saved\SaveGames
```

The active save is usually named `<SteamID>.save`.

**Always back up your entire `SaveGames` folder outside the game directory before editing.** Keep the original file and the game's own backups until you've confirmed everything works.

## Troubleshooting

**The game marks my save as corrupt or restores a backup**  
Make sure you're using **v10**, not v8 or v9. Close the game before editing, and confirm you're using the active save file.

**The editor doesn't open**  
Make sure you extracted all files from the ZIP. Open Command Prompt in the extracted folder and run:

```cmd
py -3 save_editor_gui.py
```

**I get a missing `Crypto` module error**  
Run:

```cmd
py -3 -m pip install pycryptodome
```

**Frost or Cactus can't be edited**  
Level that magic naturally at least once, save in-game, and reopen the save in the editor.

If you run into a bug, open an issue with the game version, editor version, steps to reproduce it, and the error message. Please don't post unredacted personal save data publicly.

## Version history

- **v10:** Fixed the `FFWT` CRC32 checksum so edited saves load after the Fear Fear West update. Kept the backup and validation safeguards.
- **v9:** Experimental encryption/write safeguards; did not resolve the game's corruption detection.
- **v8:** Fixed Frost/Cactus level editing using the actual XP records.

## Disclaimer

This is an unofficial community tool, not affiliated with the developers or publisher of Far Far West. Game updates may change the save format. Keep backups of your original saves.
