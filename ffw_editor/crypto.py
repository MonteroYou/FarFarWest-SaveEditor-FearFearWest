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


V2_TAIL = bytes.fromhex("464bbcf4")  # Observed four-byte trailer in current game saves.


def split_save(data: bytes) -> tuple[bytes, bytes]:
    """Separate the AES envelope from the optional newer-format tail.

    Refuse unknown trailing data rather than silently discarding it.
    """
    if len(data) >= 36 and len(data) % 16 == 4 and data[-4:] == V2_TAIL:
        return data[:-4], data[-4:]
    if len(data) >= 32 and len(data) % 16 == 0:
        return data, b""
    raise ValueError(f"Unrecognized save envelope (size {len(data)}); refusing to edit")


def decrypt(data: bytes, key: bytes) -> bytes:
    data, _tail = split_save(data)
    iv, ct = data[:16], data[16:]
    pt = AES.new(key, AES.MODE_CBC, iv=iv).decrypt(ct)
    if pt[:4] != b"GVAS":
        raise ValueError(f"decrypt produced non-GVAS magic: {pt[:8].hex()}")
    return pt


def encrypt(plaintext: bytes, key: bytes, iv: bytes | None = None, tail: bytes = b"") -> bytes:
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
    if tail not in (b"", V2_TAIL):
        raise ValueError("Unknown save trailer; refusing to write")
    return iv + ct + tail


def decrypt_file(path: str | Path, key: bytes) -> bytes:
    return decrypt(Path(path).read_bytes(), key)


def encrypt_file(plaintext: bytes, path: str | Path, key: bytes) -> None:
    Path(path).write_bytes(encrypt(plaintext, key))
