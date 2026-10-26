"""
Preset transformations for FarFarWest saves.

Each preset operates on the parsed `playerProgress` struct (a list of
property dicts as produced by GvasFile.parse). Presets only *modify in
place* — they don't add new inventory entries (which would need cloned
metadata) — so they can only toggle / max things the player already has.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
from .i18n import I18N

INT32_MAX = 2147483647


def _short(name: str) -> str:
    return name.split("_", 1)[0]


def _find(props: list[dict], prefix: str) -> dict | None:
    return next((p for p in props if p["_name"].startswith(prefix)), None)


def _inventory_entries(props: list[dict]):
    inv = _find(props, "runtimeInventory")
    if not inv:
        return
    for entry in inv["value"]:
        name_p = next((p for p in entry if _short(p["_name"]) == "name"), None)
        amt_p = next((p for p in entry if _short(p["_name"]) == "amount"), None)
        if name_p and amt_p:
            yield str(name_p["value"]), amt_p


def _challenges(props: list[dict]):
    ch = _find(props, "challenges")
    return ch["value"]["items"] if ch else []


def _find_inventory_amount(props, item_name: str):
    aliases = {
        "itemIce": ("itemIce", "itemFrost"),
        "itemFrost": ("itemFrost", "itemIce"),
        "itemCactus": ("itemCactus",),
    }.get(item_name, (item_name,))
    for name, amount in _inventory_entries(props):
        if name in aliases:
            return amount
    return None


# --- preset implementations ----------------------------------------------

def preset_max_money(props):
    n = 0
    for name, amt in _inventory_entries(props):
        if name.startswith("money") or "candle" in name.lower():
            amt["value"] = 999_999
            n += 1
    return I18N.t("msg_currency_stacks", n=n)


def preset_max_item_levels(props):
    n = 0
    for item in _challenges(props):
        key = str(item["key"])
        if key.startswith("item") and key.endswith("Lvl"):
            item["value"] = 100
            n += 1
            # Synchronize only a game-created XP record. Never add entries.
            amount = _find_inventory_amount(props, key[:-3])
            if amount is not None:
                amount["value"] = 100_000
    return I18N.t("msg_item_levels", n=n)


def preset_unlock_difficulties(props):
    p = _find(props, "unlockedDifficulties")
    if p:
        p["value"] = 4
        return I18N.t("msg_unlocked_diff")
    return I18N.t("err_diff_not_found")


def _set_owned_by_prefix(props, prefix: str, label_key: str):
    n = 0
    for name, amt in _inventory_entries(props):
        if name.startswith(prefix):
            if amt["value"] < 1:
                amt["value"] = 1
            n += 1
    return I18N.t("msg_owned_label", n=n, label=I18N.t(label_key))


def preset_unlock_skins(props):     return _set_owned_by_prefix(props, "skin",  "label_skins")
def preset_unlock_mounts(props):    return _set_owned_by_prefix(props, "mount", "label_mounts")
def preset_unlock_emotes(props):    return _set_owned_by_prefix(props, "emote", "label_emotes")
def preset_unlock_titles(props):    return _set_owned_by_prefix(props, "title", "label_titles")
def preset_unlock_maps(props):      return _set_owned_by_prefix(props, "map",   "label_maps")


def preset_unlock_jokers(props):
    n = 0
    for name, amt in _inventory_entries(props):
        if name.startswith("joker") and amt["value"] < 1:
            amt["value"] = 1
            n += 1
    return I18N.t("msg_unlocked_jokers", n=n)


def preset_stack_items(props):
    """Stack consumable / weapon items to 99,999. Skips fragments,
    prestige unlocks, upgrade slot counters, and the special weapons."""
    skip_suffixes = ("Fragment", "Prestige")
    n = 0
    for name, amt in _inventory_entries(props):
        if not name.startswith("item"):
            continue
        if any(name.endswith(s) for s in skip_suffixes):
            continue
        if name.startswith("upgradeSlot"):
            continue
        amt["value"] = 99_999
        n += 1
    return I18N.t("msg_stacked_items", n=n)


# Per-item upgrade caps. Conservative: pick a value that the player has
# already reached for that key somewhere in this save, so the game accepts
# it. For things we haven't seen we fall back to 99.
UPGRADE_CAPS = {
    "itemHero":        {"jokerUpgradeJumpHeight": 10, "jokerUpgradeHeroSpeed": 10,
                        "jokerUpgradeSpellCooldownReduction": 10, "jokerUpgradeHeal": 10},
    "itemBoomerang":   {"jokerUpgradeBoomerangRange": 10, "jokerUpgradeBoomerangLingeringTime": 10,
                        "jokerUpgradeDrawSpeed": 10, "jokerUpgradeLifesteal_Lower": 10},
    "itemQuadCylinder":{"jokerUpgradeFireRate": 10, "jokerUpgradeClipSize": 10},
    "itemBow":         {"jokerUpgradeBendSpeed": 16, "jokerUpgradeDrawSpeed": 16,
                        "jokerUpgradeTotalAmmoBagB": 16, "jokerUpgradeDamage": 16},
    "itemDualRevolver":{"jokerUpgradeDrawSpeed": 16, "jokerUpgradeAccuracy": 16,
                        "jokerUpgradeDamage": 16, "jokerUpgradeReloadSpeed": 16},
    "itemShotgun":     {"jokerUpgradeFireRate": 16, "jokerUpgradeAccuracy": 16,
                        "jokerUpgradeDrawSpeed": 16, "jokerUpgradeReloadSpeed": 16,
                        "jokerUpgradeClipSize": 16, "jokerUpgradeDamage": 16},
    "itemMinigun":     {"jokerUpgradeAccuracy": 16, "jokerUpgradeFirerateB": 16,
                        "jokerUpgradeDamage": 16, "jokerUpgradeTotalAmmoBagC": 16,
                        "jokerUpgradeDrawSpeed": 16},
    "itemLongRanger":  {"jokerUpgradeFireRate": 16, "jokerUpgradeClipSize": 16},
}


def preset_max_upgrades(props):
    ups = _find(props, "itemsUpgrades")
    if not ups:
        return "itemsUpgrades not found"
    n = 0
    for item in ups["value"]["items"]:
        item_name = str(item["key"])
        tweaks_p = next((p for p in item["value"] if _short(p["_name"]) == "tweaks"), None)
        if not tweaks_p:
            continue
        caps = UPGRADE_CAPS.get(item_name, {})
        for tw in tweaks_p["value"]["items"]:
            cap = caps.get(str(tw["key"]), max(int(tw.get("value", 0)), 16))
            tw["value"] = cap
            n += 1
    return I18N.t("msg_maxed_upgrades", n=n)


def preset_complete_challenges(props):
    rewarded_p = _find(props, "rewardedChallenges")
    challenges_p = _find(props, "challenges")
    if not rewarded_p or not challenges_p:
        return I18N.t("err_challenges_not_found")
    have = set(rewarded_p["value"])
    added = 0
    for item in challenges_p["value"]["items"]:
        key = str(item["key"])
        # Only synth-able challenges we know exist as rewards follow the
        # naming convention used in rewardedChallenges. Stat counters
        # (killEnemy, etc) aren't rewards. Filter to those starting with
        # "challenge".
        # However the game's rewarded list uses names like
        # "challengeWinNormal" rather than the raw counter "Normal". So
        # we only push entries already shaped like challenge IDs.
        if key.startswith("challenge") and key not in have:
            rewarded_p["value"].append(key)
            have.add(key)
            added += 1
    return I18N.t("msg_challenges_rewarded", added=added, total=len(have))


def preset_equip_legend_title(props):
    title_p = _find(props, "title")
    if title_p:
        title_p["value"] = "titleLegendOfTheFarFarWest"
        return I18N.t("msg_equipped_legend")
    return I18N.t("err_title_not_found")


# --- registry ------------------------------------------------------------

@dataclass
class Preset:
    key: str
    name: str
    description: str
    apply: Callable[[list[dict]], str]


PRESETS: list[Preset] = [
    Preset("money",        "preset_money_name",
           "preset_money_desc",
           preset_max_money),
    Preset("levels",       "preset_levels_name",
           "preset_levels_desc",
           preset_max_item_levels),
    Preset("upgrades",     "preset_upgrades_name",
           "preset_upgrades_desc",
           preset_max_upgrades),
    Preset("difficulties", "preset_difficulties_name",
           "preset_difficulties_desc",
           preset_unlock_difficulties),
    Preset("skins",        "preset_skins_name",
           "preset_skins_desc",
           preset_unlock_skins),
    Preset("mounts",       "preset_mounts_name",
           "preset_mounts_desc",
           preset_unlock_mounts),
    Preset("emotes",       "preset_emotes_name",
           "preset_emotes_desc",
           preset_unlock_emotes),
    Preset("titles",       "preset_titles_name",
           "preset_titles_desc",
           preset_unlock_titles),
    Preset("maps",         "preset_maps_name",
           "preset_maps_desc",
           preset_unlock_maps),
    Preset("jokers",       "preset_jokers_name",
           "preset_jokers_desc",
           preset_unlock_jokers),
    Preset("items",        "preset_items_name",
           "preset_items_desc",
           preset_stack_items),
    Preset("challenges",   "preset_challenges_name",
           "preset_challenges_desc",
           preset_complete_challenges),
    Preset("legend",       "preset_legend_name",
           "preset_legend_desc",
           preset_equip_legend_title),
]


def apply_presets(props: list[dict], keys: list[str]) -> list[str]:
    by_key = {p.key: p for p in PRESETS}
    log = []
    for k in keys:
        preset = by_key.get(k)
        if not preset:
            continue
        try:
            log.append(f"[{I18N.t(preset.name)}] {preset.apply(props)}")
        except Exception as exc:
            log.append(f"[{I18N.t(preset.name)}] FAILED: {exc}")
    return log
