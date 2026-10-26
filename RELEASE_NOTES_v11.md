v11.0 — Prestige & Currencies Update
This release adds Hero prestige rewards and currency editing to the existing Far Far West Save Editor, while retaining the v10 FFWT checksum fix.
New
Hero prestige: Apply one prestige at a time (up to 15), selecting rewards with five tokens per application.
Prestige rewards: Hero Joker slot (5 tokens), Hero upgrade slots (2 tokens each), XP ticket (1 token), 500 gold (1 token), or 1,000 souls (1 token).
Currencies page: Edit existing Gold, Souls, XP tickets, Blueprints (`moneyBlueprint`) and Haunted Candles (`moneyHauntedCandle`) entries.
Blueprints and Haunted Candles: Both field names have been identified from game-generated saves; currency editing has been confirmed working in-game.
Kept / fixed
FFWT CRC32 validation and recalculation from v10.
Encrypted output read-back checks and original-save backup protections.
Frost and Cactus magic support.
Important
Hero prestige only; weapon prestige is not included.
The prestige editor applies one prestige transaction at a time and requires spending all five tokens.
Currency editing uses existing save records; you may need to earn a currency naturally before it appears in the editor.
Back up your entire SaveGames folder before editing.
Install
Download `FarFarWest_SaveEditor_v11_Prestige_and_Currencies.zip`, extract it completely, close the game, then run `run_editor.bat` on Windows (Python 3 required).
Tested with Fear Fear West v0.3.0.7. This release bundles the previously tested v11.2 prestige upgrade-slot implementation and the v11.1 currency editor; no game files are modified directly.
