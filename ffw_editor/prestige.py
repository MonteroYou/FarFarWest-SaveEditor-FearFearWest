"""Hero prestige transaction: one level, game-tested reward fields."""
from __future__ import annotations
import copy
import struct
import zlib


def short(name):
    return name.split("_", 1)[0]


def player_props(gvas):
    return next(p["value"] for p in gvas.properties if p["_name"] == "playerProgress")


def prop(props, prefix):
    return next((p for p in props if p["_name"].startswith(prefix)), None)


def inventory(props):
    p = prop(props, "runtimeInventory")
    if p is None: raise ValueError("runtimeInventory not present")
    return p["value"]


def records(props):
    out = {}
    for entry in inventory(props):
        name = next((p for p in entry if short(p["_name"]) == "name"), None)
        amount = next((p for p in entry if short(p["_name"]) == "amount"), None)
        if name is not None and amount is not None:
            out[name["value"]] = amount
    return out


def inventory_set(props, key, value):
    if not 0 <= value <= 2147483647: raise ValueError("Inventory value outside int32 range")
    old = records(props)
    if key in old:
        old[key]["value"] = value
        return
    inv = inventory(props)
    # Clone a game-created inventory entry to preserve metadata layout.
    template_key = "moneyGold" if key == "moneyTicket" else "itemHero"
    source = next((entry for entry in inv if any(short(p["_name"]) == "name" and p["value"] == template_key for p in entry)), None)
    if source is None: raise ValueError("Cannot find a game-created Hero inventory template")
    new = copy.deepcopy(source)
    for field in new:
        if short(field["_name"]) == "name":
            field["value"] = key
            field.pop("_raw_value", None)
        elif short(field["_name"]) == "amount":
            field["value"] = value
    inv.append(new)


def challenge_set(props, key, value):
    p = prop(props, "challenges")
    if p is None: raise ValueError("Missing challenges map")
    items = p["value"]["items"]
    item = next((x for x in items if x["key"] == key), None)
    if item is None: items.append({"key": key, "value": value})
    else: item["value"] = value


def state(gvas):
    props = player_props(gvas)
    inv = records(props)
    ch = prop(props, "challenges")
    counts = {i["key"]: i["value"] for i in ch["value"]["items"]} if ch else {}
    return {"prestige": int(inv.get("itemHeroPrestige", {"value":0})["value"]),
            "joker": int(inv.get("jokerSlotitemHero", {"value":0})["value"]),
            "upgrade_slots": int(inv.get("upgradeSlotitemHero", {"value":0})["value"]),
            "xp": int(inv.get("itemHero", {"value":0})["value"]),
            "challenges": counts}


def apply_hero_prestige(gvas, joker_slot=False, tickets=0, gold_packs=0, soul_packs=0, upgrade_slots=0):
    """Apply one Hero prestige with a fully allocated five-token reward budget."""
    vals = (tickets, gold_packs, soul_packs, upgrade_slots)
    if any(type(x) is not int or x < 0 for x in vals):
        raise ValueError("Rewards must be nonnegative whole numbers")
    if type(joker_slot) is not bool: raise ValueError("Invalid Joker slot choice")
    if joker_slot * 5 + tickets + gold_packs + soul_packs + 2 * upgrade_slots != 5:
        raise ValueError("All five prestige tokens must be allocated")
    props = player_props(gvas)
    before = state(gvas)
    if before["prestige"] >= 15: raise ValueError("Hero prestige cap reached (15)")
    if joker_slot and before["joker"] >= 2: raise ValueError("Hero Joker slot cap reached (2)")
    if before["upgrade_slots"] + upgrade_slots > 6: raise ValueError("Hero additional upgrade-slot cap reached (6)")
    changes = {"itemHero": 1}
    if joker_slot: changes["jokerSlotitemHero"] = before["joker"] + 1
    if upgrade_slots: changes["upgradeSlotitemHero"] = before["upgrade_slots"] + upgrade_slots
    changes["itemHeroPrestige"] = before["prestige"] + 1
    for key, amount in (("moneyTicket", tickets), ("moneyGold", 500*gold_packs), ("moneySoul", 1000*soul_packs)):
        if amount:
            if key not in records(props) and key != "moneyTicket":
                raise ValueError(f"Missing game-created {key} entry; this reward is unavailable")
            changes[key] = int(records(props)[key]["value"]) + amount if key in records(props) else amount
    for key,val in changes.items(): inventory_set(props,key,val)
    # Game-created first prestige updates these two challenge counters.
    ch = before["challenges"]
    challenge_set(props, "Prestige", int(ch.get("Prestige",0)) + 1)
    challenge_set(props, "prestigeitemHero", int(ch.get("prestigeitemHero",0)) + 1)
    return before, state(gvas)


def rebuilt_ffwt(gvas):
    """Rebuild FFWT version 1 with CRC32 and correct PKCS7 length when records grow."""
    trailing = gvas.trailing
    idx = trailing.rfind(b"FFWT")
    if idx < 0 or idx + 16 > len(trailing): raise ValueError("Missing FFWT footer")
    ver, old_length, _old_crc = struct.unpack_from("<III", trailing, idx + 4)
    if ver != 1: raise ValueError("Unrecognized FFWT version")
    if idx + 16 >= len(trailing): raise ValueError("Missing AES padding")
    pad=trailing[-1]
    if not (1 <= pad <= 16 and trailing[-pad:] == bytes([pad])*pad and idx+16==len(trailing)-pad):
        raise ValueError("Unrecognized FFWT padding")
    # Retain any opaque bytes immediately preceding FFWT (observed 4 zero bytes).
    gvas.trailing = trailing[:idx]
    prefix=gvas.serialize()
    end=prefix+b"FFWT"+struct.pack("<III",1,len(prefix),zlib.crc32(prefix)&0xffffffff)
    padding=16-len(end)%16
    gvas.trailing=trailing[:idx]+b"FFWT"+struct.pack("<III",1,len(prefix),zlib.crc32(prefix)&0xffffffff)+bytes([padding])*padding
    return gvas.serialize()
