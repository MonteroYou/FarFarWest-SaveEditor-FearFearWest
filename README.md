# Far Far West Save Editor — Frost & Cactus Magic Fix

Community-maintained Python save editor for **Far Far West**, with safe support for Frost and Cactus magic progression.

## v8 highlights

- Edits the real, game-created Frost XP record (`itemIce`).
- Edits the real, game-created Cactus XP record (`itemCactus`).
- Uses existing XP records only; it does **not** invent new `runtimeInventory` entries.
- Preserves the byte-preserving GVAS serialization approach.
- Keeps `rewardedChallenges` intact.
- Retains the editor's original AES encryption/decryption implementation.
- Includes a Windows `run_editor.bat` launcher.

## Important requirement

Before Frost or Cactus can be edited, **level each magic naturally in-game at least once** so the game creates its legitimate `itemIce` / `itemCactus` XP record. v8 intentionally refuses to manufacture missing records because doing so was found to make saves unusable.

Always back up your save before editing it.

## Running on Windows

1. Download and extract the release ZIP.
2. Double-click `run_editor.bat`.
3. Select your Far Far West save.
4. Make your changes and save.

The launcher checks for Python and installs `pycryptodome` if necessary.

## Source

The Python source is in `ffw_editor/`. The GUI entry point is `save_editor_gui.py`.

## Disclaimer

This is an unofficial community tool and is not affiliated with or endorsed by the developers or publisher of Far Far West. Save formats can change between game versions. Keep backups of original saves.

## Credits / original project

This version is based on an existing Far Far West Save Editor and modifies its Python source to add/fix Frost and Cactus progression support. Add the original author's/project link here if known so proper attribution is preserved.
