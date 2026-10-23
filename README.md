Far Far West Save Editor — Frost & Cactus Magic Fix
Save editor for Far Far West, updated for the Fear Fear West game update.
v10 — Fear Fear West fix
Fixed edited saves being detected as corrupt and replaced by the game's automatic backup.
The game stores an `FFWT` footer containing a CRC32 checksum of the GVAS save data. Previous versions changed the save values without updating that checksum. v10 recalculates the CRC32 when saving and validates it when reading a file.
I tested v10 in-game and confirmed the edited save loads properly.
Features
Edit gold and the other values supported by the editor.
Edit Frost and Cactus magic levels using the existing `itemIce` and `itemCactus` XP records.
Preserve the original save structure without adding fake inventory records.
Verify the `FFWT` checksum and the output file after editing.
Create a backup before replacing an existing save.
Frost and Cactus requirement: Level the relevant magic naturally at least once in-game before editing it. The game must first create the corresponding XP record. The editor won't create missing XP records.
Download and run (Windows)
Download `FarFarWest_SaveEditor_v10_FearFearWest_FIXED.zip`.
Extract the entire ZIP to a folder.
Close Far Far West completely.
Double-click `run_editor.bat`. Python 3 is required; the launcher will attempt to install `pycryptodome` if it's missing.
Click Open, select your save, change the values you want, then click Save.
Launch the game to check the changes.
Save files are normally in:
```text
%LOCALAPPDATA%\FarFarWest\Saved\SaveGames
```
The active save is normally `<SteamID>.save`. Back up the entire SaveGames folder somewhere else before using the editor. Don't replace or delete the game's backups unless you have copies elsewhere.
Troubleshooting
Game marks the save as corrupt or restores a backup: Make sure you're using v10, not v8 or v9. Check that the game is closed while editing and that you're loading the correct save file.
Editor doesn't open: Make sure everything was extracted, then run `py -3 save_editor_gui.py` in Command Prompt from the extracted folder to see the error.
Missing Crypto module: Run `py -3 -m pip install pycryptodome`.
Frost/Cactus editing isn't available: Level the magic at least once naturally, save in-game, then reopen that save in the editor.
Please include the game version, editor version, what you tried, and the error message when reporting an issue. Avoid posting unredacted personal save data publicly.
Version history
v10: Fixed the `FFWT` CRC32 checksum so the game accepts edited saves after the Fear Fear West update; retained validation and backup safeguards.
v9: Experimental encryption/write safety changes. Did not solve game-side corruption.
v8: Fixed Frost/Cactus magic editing using their actual XP records.
Disclaimer
This is an unofficial community tool, not affiliated with the developers or publisher of Far Far West. Save formats can change between game updates. Always keep backups.
