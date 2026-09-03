# v8 — Frost & Cactus Magic Fix

## Fixed

- Frost and Cactus level editing now targets their real game-created XP records:
  - Frost: `itemIce`
  - Cactus: `itemCactus`
- The GUI derives Frost/Cactus effective levels from XP rather than relying on the separate challenge counters.
- No synthetic Frost/Cactus `runtimeInventory` records are created.

## Safety

- Existing inventory records are preserved.
- `rewardedChallenges` is left intact.
- AES behavior remains unchanged from the original editor.
- Byte-preserving GVAS handling is retained.

## Required first step

Frost and Cactus must each have been levelled naturally in-game at least once before editing, so the save contains legitimate XP records. If one is missing, v8 does not create it.

Back up saves before editing.
