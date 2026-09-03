Far Far West Save Editor - Frostburn Magic Fixed v8

This build is based on v7 SAFE and keeps the no-synthetic-inventory rule.

Confirmed from a save where Frost and Cactus were levelled naturally:
- Frost gameplay XP is stored in runtimeInventory as itemIce.
- Cactus gameplay XP is stored in runtimeInventory as itemCactus.
- itemIceLvl / itemCactusLvl can be stale challenge/progression counters and
  are not authoritative for the in-game magic level.

v8 changes:
- Frost/Cactus level rows display the effective level derived from existing XP.
- Editing those rows changes only the existing 4-byte XP amount and synchronizes
  the counter.
- No runtimeInventory entries are created.
- If the save has never naturally created the XP entry, v8 will not invent it.
- AES crypto code is unchanged.
- rewardedChallenges is untouched.

For the supplied naturally-levelled save, itemIce=2022 and itemCactus=1944,
which correspond to effective levels 3 and 2 respectively.
