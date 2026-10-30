# v11.1 — Save Format Compatibility Fix

## Fixed

- Fixed the `bad save size` error affecting newer Far Far West save files.
- Added support for the updated FFWT v2 save format.
- Added handling for the new four-byte trailer while preserving the existing AES encryption.
- Updated CRC32 checksum validation and recalculation to support both formats.

## Compatibility

- Supports older FFWT v1 saves.
- Supports newer FFWT v2 saves.
- Keeps the Prestige Editor and all existing currency features from v11.

## Testing

Confirmed that previously unsupported saves can now be opened, edited, and loaded successfully in-game.

## Installation

Download the latest ZIP, extract it completely, and launch `run_editor.bat`.

Always back up your original save files before editing.
