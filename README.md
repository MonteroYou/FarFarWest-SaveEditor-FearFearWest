# Far Far West Save Editor — Fear Fear West

Save editor for **Far Far West**, updated for the **Fear Fear West** game update. Supports Hero prestige rewards, currency editing, Frost/Cactus magic editing, and the FFWT checksum required for edited saves to load.

## Download

**[Download the latest release](https://github.com/MonteroYou/FarFarWest-SaveEditor-FearFearWest/releases/latest)** and choose `FarFarWest_SaveEditor_v11_Prestige_and_Currencies.zip` under **Assets**. Extract the ZIP before running the editor; do not run the launcher from inside the ZIP.

## Features

### Hero prestige

The **Prestige** page adds **one Hero prestige per application**, up to Prestige 15, and requires spending all **five reward tokens** for that prestige. The supported choices follow the in-game menu:

| Reward | Cost | Limit |
| --- | ---: | --- |
| Extra Hero Joker slot | 5 tokens | 2 additional slots |
| Extra Hero upgrade slot | 2 tokens | 6 additional slots |
| XP ticket | 1 token | Available while tokens remain |
| 500 gold | 1 token | Available while tokens remain |
| 1,000 souls | 1 token | Available while tokens remain |

The editor preserves previously earned rewards. **This feature edits Hero prestige only**, not weapon prestige. Each application also resets Hero XP, as the game does when prestiging. Make a backup before editing.

### Currencies

The **Currencies** page edits existing, game-created currency records, including:

| Currency | Save record |
| --- | --- |
| Gold | `moneyGold` |
| Souls | `moneySoul` |
| XP tickets | `moneyTicket` |
| Blueprints | `moneyBlueprint` |
| Haunted Candles | `moneyHauntedCandle` |

**Blueprints and Haunted Candles have been confirmed in actual game saves and tested in-game.** The Currencies page lists currencies present in the opened save rather than inventing arbitrary missing records. To edit Haunted Candles directly, first earn some in-game so `moneyHauntedCandle` exists in the save. The prestige reward path can create a missing XP-ticket record when needed.

### Other edits

- Frost and Cactus magic progression, using existing `itemIce` and `itemCactus` XP records
- Existing inventory, upgrade, Joker, challenge and preset features
- FFWT CRC32 checksum validation and recalculation to prevent the corrupted-save rollback fixed in v10
- Save backups and write verification

**Frost and Cactus requirement:** Level each magic naturally at least once before editing, so the game creates its actual XP record.

## Install and use (Windows)

1. Download the ZIP from [Releases](https://github.com/MonteroYou/FarFarWest-SaveEditor-FearFearWest/releases/latest).
2. Extract the **entire** ZIP into its own folder.
3. Close the game completely.
4. Double-click `run_editor.bat` (Python 3 required). The launcher will attempt to install `pycryptodome` if missing.
5. Choose **Open**, select your active `.save` file, make edits, then click **Save**.
6. Launch the game and confirm the changes appear.

### Save location

```text
%LOCALAPPDATA%\FarFarWest\Saved\SaveGames
```

The active file is usually named `<SteamID>.save`. **Back up your entire `SaveGames` folder outside the game's save directory** before editing. Keep your originals and game backups until you have confirmed the changes.

## Troubleshooting

- **Game restores a backup or marks the save corrupt:** Use the latest version with FFWT CRC32 support; make sure the game was closed and you're editing the active save.
- **Editor does not open:** Extract all files and run `py -3 save_editor_gui.py` from a Command Prompt opened in the extracted folder to see the error.
- **Missing Crypto module:** Run `py -3 -m pip install pycryptodome`.
- **A currency is not listed:** The game may not have created that currency record yet; earn some normally and save once.
- **Prestige option not working:** Verify Hero progress and select a valid combination spending exactly five tokens. This does not affect weapon prestige.

Report bugs through [GitHub Issues](https://github.com/MonteroYou/FarFarWest-SaveEditor-FearFearWest/issues). Include the game version, editor version, reproduction steps and error text; do not post saves containing personal identifiers publicly.

## Version history

- **v11 — Prestige & Currencies:** Hero prestige reward allocation; Joker slots, upgrade slots, XP tickets, gold and souls; currency editor including tested Blueprints and Haunted Candles.
- **v10 — Save integrity:** Fixed the FFWT CRC32 checksum after editing to stop saves being rejected and backups being restored.
- **v8 — Frost/Cactus:** Added XP-backed Frost and Cactus editing.

## Attribution / disclaimer

Unofficial community tool; not endorsed by the game's developers or publisher. Derived from previous community editor work. See `LICENSE_NOTICE.md` for the current attribution/licensing notice. Always retain backups; game updates may change the save format.
