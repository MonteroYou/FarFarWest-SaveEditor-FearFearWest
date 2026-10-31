# v11.4 — Multi-Account Save Compatibility Fix

## Fixed

- Fixed `Unrecognized save envelope`, `Save footer/trailer format mismatch`, and FFWT footer errors for supported newer saves with varying per-save FFWT v2 identifiers.
- Replaced a fixed per-save identifier assumption with validation that the internal FFWT v2 identifier agrees with the external four-byte trailer.
- Preserves the original trailer and footer version on write and recalculates the FFWT CRC32 checksum.
- Keeps AES-CBC encryption, save backups, read-back verification and older FFWT v1 compatibility.

## Retained

- Hero prestige and all five prestige reward options
- Gold, Souls, XP tickets, Blueprints and Haunted Candles
- Frost/Cactus progression editing

## Testing

The format fix has been confirmed working in-game by three testers, including the reporter of Issue #2. Other save variants and future updates are not guaranteed.

## Known issue

On some Windows systems, drag-and-drop can trigger an `OverflowError`. Please use the **Open** button to select the file. This is separate from FFWT compatibility.

Back up your entire `SaveGames` folder outside the game directory before editing.
