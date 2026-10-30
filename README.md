# Far Far West Save Editor — Fear Fear West

A save editor for **Far Far West**, updated for the **Fear Fear West** game update.

Supports Hero prestige rewards, currency editing, Frost/Cactus magic progression, and FFWT checksum validation to ensure edited saves load correctly.

## Download

**[Download the latest release](https://github.com/MonteroYou/FarFarWest-SaveEditor-FearFearWest/releases/latest)**

Download the latest version's ZIP file under **Assets**.

Extract the entire ZIP before running the editor. Do not run the launcher directly from inside the ZIP.

**Requirements:**
- Windows
- Python 3
- `pycryptodome` (automatically installed by the launcher if missing)

---

## Features

### Hero Prestige

The **Prestige** page allows you to increase your Hero prestige level and select the corresponding rewards.

- Increase Hero prestige **one level at a time**, up to Prestige 15.
- Receive five reward tokens for each prestige.
- Allocate all five tokens across the available rewards.
- Preserve previously earned prestige rewards.
- Automatically reset Hero XP when applying a prestige.

| Reward | Token cost | Limit |
|---|---:|---|
| Extra Hero Joker slot | 5 | 2 additional slots |
| Extra Hero upgrade slot | 2 | 6 additional slots |
| XP ticket | 1 | Available while tokens remain |
| 500 Gold | 1 | Available while tokens remain |
| 1,000 Souls | 1 | Available while tokens remain |

**Important:** Prestige editing currently supports **Hero prestige only**, not individual weapon prestige.

Always back up your save before modifying prestige progression.

### Currencies

The **Currencies** page allows you to edit existing currency records stored in your save.

| Currency | Save record |
|---|---|
| Gold | `moneyGold` |
| Souls | `moneySoul` |
| XP Tickets | `moneyTicket` |
| Blueprints | `moneyBlueprint` |
| Haunted Candles | `moneyHauntedCandle` |

Blueprints and Haunted Candles have been identified in actual game saves and tested in-game.

The editor only displays currency records already present in your save, rather than creating arbitrary missing records.

**Note:** To edit Haunted Candles directly, first earn some naturally in-game so the game creates the `moneyHauntedCandle` record.

The Prestige Editor can create a missing XP Ticket record when awarding tickets.

### Frost & Cactus Magic

Supports editing Frost and Cactus magic progression using the actual XP records:

- Frost Magic: `itemIce`
- Cactus Magic: `itemCactus`

**Requirement:** You must level each magic naturally at least once in-game before editing it.

This ensures the corresponding XP records exist. The editor intentionally avoids creating fake magic inventory records, which could make saves unusable.

### Additional Features

- Edit existing inventory values.
- Modify item progression and upgrades.
- Edit Joker-related values.
- Edit challenge progression.
- Use built-in editing presets.
- Automatic save backups.
- Save validation and verification.
- FFWT CRC32 checksum recalculation.

---

## v11.1 — Save Format Compatibility Fix

Version 11.1 fixes the **`bad save size`** error affecting saves created using the newer Fear Fear West save format.

Previously, the editor expected all encrypted save files to follow the original layout. Some newer saves contain an additional four-byte trailer and use an updated FFWT footer format.

As a result, the editor would reject these files before attempting to decrypt them.

### What's Fixed

- Fixed the `bad save size` error when opening newer saves.
- Added support for the updated **FFWT v2** save format.
- Retained compatibility with older **FFWT v1** saves.
- Added handling for the additional four-byte trailer.
- Preserved the original encryption method.
- Updated CRC32 checksum validation and recalculation for both formats.
- Preserved the existing automatic backup and save verification safeguards.

### Compatibility

The editor now supports both:

- **FFWT v1:** Older save files.
- **FFWT v2:** Newer save files containing the additional trailer.

The editor recognizes the appropriate format when opening a save and preserves its required structure when writing changes.

**Tested in-game:** A save that previously failed with `bad save size` was successfully opened, edited, and loaded in-game using v11.1.

All existing Prestige Editor and currency features have been retained.

---

## Installation (Windows)

1. Download the latest ZIP from the [Releases page](https://github.com/MonteroYou/FarFarWest-SaveEditor-FearFearWest/releases/latest).
2. Extract the **entire ZIP** into its own folder.
3. Close Far Far West completely.
4. Double-click `run_editor.bat`.
5. The launcher checks for Python and attempts to install `pycryptodome` if necessary.
6. Click **Open** and select your save file.
7. Make your changes and click **Save**.
8. Launch the game and confirm the changes appear.

### Save Location

Far Far West saves are normally located at:

```text
%LOCALAPPDATA%\FarFarWest\Saved\SaveGames
```

The active save is usually named:

```text
<SteamID>.save
```

**Always back up your entire `SaveGames` folder somewhere outside the game's save directory before editing.**

Keep your original saves and game-generated backups until you've confirmed everything works.

---

## Save Integrity & Backups

Far Far West uses encrypted save files containing an **FFWT CRC32 checksum**.

The checksum allows the game to detect when the save contents do not match their recorded integrity value.

Earlier versions of the editor modified save values without updating this checksum, causing the game to mark edited saves as corrupted and restore automatic backups.

This was fixed in v10.

The editor now:

1. Decrypts and validates the save.
2. Reads and modifies the requested values.
3. Recalculates the FFWT CRC32 checksum.
4. Preserves the required save structure.
5. Encrypts the updated data.
6. Verifies the written save.

Before overwriting an existing save, the editor also creates a timestamped backup using a filename similar to:

```text
<SteamID>.backup_gui_YYYYMMDD_HHMMSS.save
```

The game may also generate its own `.save.bak` and timestamped backup files.

**Do not delete your original backups until you've confirmed that your edited save works.**

---

## Troubleshooting

### "bad save size" error

Make sure you're running **v11.1 or newer**.

Earlier versions did not support the updated FFWT v2 save format used by some newer game saves.

Download the latest version from the Releases page and extract it into a new folder.

### Game marks the save as corrupted

- Make sure you're using the latest editor version.
- Close the game completely before editing.
- Verify you're selecting the correct active `.save` file.
- Avoid manually altering the encrypted save contents.
- Restore your original backup if the game rejects the edited file.

### Editor won't open

Make sure you extracted every file from the ZIP.

Open Command Prompt in the extracted editor folder and run:

```cmd
py -3 save_editor_gui.py
```

This should display any Python errors that prevent the editor from starting.

### Missing Crypto module

Install the required dependency:

```cmd
py -3 -m pip install pycryptodome
```

Then launch the editor again.

### Currency isn't listed

The game may not have created that currency record yet.

Earn some of the currency naturally, save the game, and reopen the updated save in the editor.

### Frost or Cactus editing isn't available

Level the corresponding magic naturally at least once so its XP record is created.

### Prestige editing isn't working

- Make sure you're editing Hero prestige, not weapon prestige.
- Select a valid reward combination costing exactly five tokens.
- Check that the selected rewards haven't reached their maximum limits.
- Save your changes with the game closed.

---

## Reporting Bugs

If you encounter a problem, please open an issue:

**[GitHub Issues](https://github.com/MonteroYou/FarFarWest-SaveEditor-FearFearWest/issues)**

Include:

- Your game version.
- The save editor version.
- A description of the problem.
- Steps to reproduce the issue.
- Any error messages or screenshots.

Please avoid publicly uploading unredacted save files containing personal account identifiers.

---

## Version History

### v11.1 — Save Format Compatibility

- Fixed `bad save size` errors affecting newer saves.
- Added support for FFWT v2.
- Added handling for the additional four-byte trailer.
- Updated checksum validation and save writing.
- Retained support for older saves and existing editor features.

### v11.0 — Prestige & Currencies

- Added Hero prestige editing up to level 15.
- Added all five Hero prestige reward types.
- Added Hero Joker slot and upgrade slot rewards.
- Added XP Ticket, Gold, and Souls prestige rewards.
- Added a dedicated Currencies page.
- Added support for Blueprints and Haunted Candles.

### v10 — Save Integrity Fix

- Fixed edited saves being rejected as corrupted.
- Added FFWT CRC32 checksum recalculation.
- Added checksum validation and safer save handling.
- Improved backup and write verification.

### v8 — Frost & Cactus Magic

- Added XP-backed Frost magic editing.
- Added XP-backed Cactus magic editing.
- Preserved existing inventory records instead of generating artificial entries.

---

## Attribution & Disclaimer

This is an unofficial community-maintained tool and is not affiliated with or endorsed by the developers or publisher of Far Far West.

The editor is derived from earlier community save editor work. See `LICENSE_NOTICE.md` for the current attribution and licensing information.

Game updates may change the save format or introduce additional compatibility requirements.

**Always keep backups of your original saves.**
