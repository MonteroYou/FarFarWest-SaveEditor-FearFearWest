"""
Command-line interface for the FarFarWest save editor.

Usage:
    python -m ffw_editor.cli decrypt <save_in>  <bin_out>     [--seed SEED | --key HEX]
    python -m ffw_editor.cli encrypt <bin_in>   <save_out>    [--seed SEED | --key HEX]
    python -m ffw_editor.cli parse   <save_in>  <json_out>    [--seed SEED | --key HEX]
    python -m ffw_editor.cli pack    <json_in>  <save_out>    [--seed SEED | --key HEX]
    python -m ffw_editor.cli roundtrip <save_in> <save_out>   [--seed SEED | --key HEX]
        # parse + reserialize + re-encrypt; useful for verifying integrity.

By default the AES key is derived from:
    <numeric save filename prefix>NicoArnoEvilRaptorFireshineRobbo

For example, <steamid>.save uses:
    <steamid>NicoArnoEvilRaptorFireshineRobbo

You can still use --seed or --key to override this for diagnostics.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path

from .crypto import derive_key, decrypt, encrypt
from .gvas   import GvasFile


PARTY_SUFFIX = "NicoArnoEvilRaptorFireshineRobbo"


def _seed_for_path(path: str | Path) -> str:
    stem = Path(path).stem
    m = re.match(r"^(\d+)", stem)
    if m is None:
        sys.exit(f"ERROR: save filename must start with a SteamID: {Path(path).name}")
    return m.group(1) + PARTY_SUFFIX


def _resolve_key(args, path: str | Path | None = None) -> bytes:
    if args.key:
        return bytes.fromhex(args.key)
    if args.seed:
        return derive_key(args.seed)
    if path is None:
        sys.exit("ERROR: no save path available for filename-based key derivation.")
    return derive_key(_seed_for_path(path))


def _add_key_args(p):
    p.add_argument("--seed", help="UTF-8 seed string (SteamID+party names)")
    p.add_argument("--key",  help="32-byte AES key as 64 hex chars")


def _file_to_json(gf: GvasFile) -> str:
    return json.dumps(
        {"header": asdict(gf.header), "properties": gf.properties,
         "pre_properties": gf.pre_properties.hex(),
         "trailing": gf.trailing.hex()},
        indent=2, ensure_ascii=False, default=str,
    )


def _json_to_file(text: str) -> GvasFile:
    from .gvas import GvasHeader, CustomVersion
    obj = json.loads(text)
    h = obj["header"]
    h["custom_versions"] = [CustomVersion(**cv) for cv in h["custom_versions"]]
    header = GvasHeader(**h)
    return GvasFile(header=header,
                    properties=obj["properties"],
                    pre_properties=bytes.fromhex(obj.get("pre_properties", "")),
                    trailing=bytes.fromhex(obj.get("trailing", "")))


def cmd_decrypt(args):
    key = _resolve_key(args, args.src)
    pt = decrypt(Path(args.src).read_bytes(), key)
    Path(args.dst).write_bytes(pt)
    print(f"[+] wrote {args.dst}  ({len(pt)} bytes, GVAS {pt[:4]==b'GVAS'})")


def cmd_encrypt(args):
    key = _resolve_key(args, args.dst)
    pt = Path(args.src).read_bytes()
    Path(args.dst).write_bytes(encrypt(pt, key))
    print(f"[+] wrote {args.dst}  ({len(pt)+16} bytes encrypted)")


def cmd_parse(args):
    key = _resolve_key(args, args.src)
    pt = decrypt(Path(args.src).read_bytes(), key)
    gf = GvasFile.parse(pt)
    Path(args.dst).write_text(_file_to_json(gf), encoding="utf-8")
    print(f"[+] parsed {len(gf.properties)} top-level properties -> {args.dst}")


def cmd_pack(args):
    key = _resolve_key(args, args.dst)
    gf = _json_to_file(Path(args.src).read_text(encoding="utf-8"))
    pt = gf.serialize()
    out = encrypt(pt, key)
    Path(args.dst).write_bytes(out)
    print(f"[+] packed -> {args.dst}  ({len(out)} bytes)")


def cmd_roundtrip(args):
    key = _resolve_key(args, args.src)
    pt = decrypt(Path(args.src).read_bytes(), key)
    gf = GvasFile.parse(pt)
    re_pt = gf.serialize()
    if re_pt != pt:
        # find first diff for diagnostics
        for i, (a, b) in enumerate(zip(re_pt, pt)):
            if a != b:
                print(f"[!] first diff at offset {i}: orig={pt[i]:02X} new={re_pt[i]:02X}")
                print(f"    +/- 16 bytes orig: {pt[max(0,i-16):i+16].hex()}")
                print(f"    +/- 16 bytes new : {re_pt[max(0,i-16):i+16].hex()}")
                break
        if len(re_pt) != len(pt):
            print(f"[!] size differs: orig={len(pt)} new={len(re_pt)}")
        sys.exit("[!] round-trip mismatch")
    Path(args.dst).write_bytes(encrypt(re_pt, key))
    print(f"[+] OK: round-trip is byte-identical. encrypted -> {args.dst}")


def main():
    ap = argparse.ArgumentParser(prog="ffw_editor")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name, fn in [("decrypt", cmd_decrypt), ("encrypt", cmd_encrypt),
                     ("parse", cmd_parse), ("pack", cmd_pack),
                     ("roundtrip", cmd_roundtrip)]:
        sp = sub.add_parser(name)
        sp.add_argument("src")
        sp.add_argument("dst")
        _add_key_args(sp)
        sp.set_defaults(func=fn)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
