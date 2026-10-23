# v10 — Fear Fear West compatibility fix

## Fixed

- Updated the `FFWT` CRC32 after making edits. Previously saves could decrypt and parse fine but would be marked corrupt in-game, triggering an automatic backup restore.
- Added footer validation on load and after writing to catch bad save output.

## Kept from v9

- File-change detection, backups, encrypted read-back checks, and conservative save handling.

## Magic editing

Frost/Cactus editing still requires the corresponding XP records to have been created in-game.

**Status:** Tested in-game with the Fear Fear West update.
