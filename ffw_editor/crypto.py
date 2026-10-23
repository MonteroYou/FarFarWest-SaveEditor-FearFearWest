"""
FarFarWest save crypto layer.

File layout (reverse-engineered):
    bytes[0..16)   = IV
    bytes[16..end) = AES-256-CBC ciphertext (multiple of 16)

Key derivation:
    key = SHA-256(seed)
    seed = <SteamID> + <party-member-names-concatenated>   (UTF-8)

The seed is rebuilt by the *game* at save time from its live state, so as
long as you don't change party between dumping the seed and writing back,
the same key keeps working across saves.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from Crypto.Cipher import AES


def derive_key(seed: str | bytes) -> bytes:
    if isinstance(seed, str):
        seed = seed.encode("utf-8")
    return hashlib.sha256(seed).digest()


def decrypt(data: bytes, key: bytes) -> bytes:
    if len(data) < 32 or (len(data) - 16) % 16 != 0:
        raise ValueError(f"bad save size {len(data)}")
    iv, ct = data[:16], data[16:]
    pt = AES.new(key, AES.MODE_CBC, iv=iv).decrypt(ct)
    if pt[:4] != b"GVAS":
        raise ValueError(f"decrypt produced non-GVAS magic: {pt[:8].hex()}")
    return pt


def encrypt(plaintext: bytes, key: bytes, iv: bytes | None = None) -> bytes:
    if plaintext[:4] != b"GVAS":
        raise ValueError("plaintext must start with GVAS")
    if len(plaintext) % 16 != 0:
        # Game writes plaintext that is already a multiple of 16. Pad with zero
        # bytes so the resulting file is the same shape; UE GVAS readers stop
        # at "None" so trailing zeros are harmless.
        plaintext += b"\x00" * (16 - (len(plaintext) % 16))
    if iv is None:
        iv = os.urandom(16)
    if len(iv) != 16:
        raise ValueError("iv must be 16 bytes")
    ct = AES.new(key, AES.MODE_CBC, iv=iv).encrypt(plaintext)
    return iv + ct


def decrypt_file(path: str | Path, key: bytes) -> bytes:
    return decrypt(Path(path).read_bytes(), key)


def encrypt_file(plaintext: bytes, path: str | Path, key: bytes) -> None:
    Path(path).write_bytes(encrypt(plaintext, key))
