"""Far Far West save payload FFWT integrity footer.

Observed format: serialized GVAS + b'FFWT' + uint32 LE(version=1) +
uint32 LE(GVAS_length) + uint32 LE(CRC32(GVAS)) + PKCS#7 AES padding.
Only process when the footer is unambiguously identified.
"""
from __future__ import annotations
import struct
import zlib


def _footer(payload: bytes) -> tuple[int, int] | None:
    # The AES CBC plaintext has PKCS#7 padding added by the game.
    if not payload or not (1 <= payload[-1] <= 16):
        return None
    pad = payload[-1]
    if payload[-pad:] != bytes([pad]) * pad:
        return None
    end = len(payload) - pad
    if end < 16 or payload[end-16:end-12] != b'FFWT':
        return None
    version, gvas_len, _crc = struct.unpack_from('<III', payload, end - 12)
    if version != 1 or gvas_len != end - 16:
        return None
    return end - 16, end


def check_checksum(payload: bytes) -> None:
    bounds = _footer(payload)
    if bounds is None:
        raise ValueError('Unrecognized or missing FFWT checksum footer; refusing to edit.')
    start, _end = bounds
    stored = struct.unpack_from('<I', payload, start + 12)[0]
    actual = zlib.crc32(payload[:start]) & 0xffffffff
    if stored != actual:
        raise ValueError(f'Save FFWT checksum mismatch (stored {stored:08X}, actual {actual:08X}); refusing to edit.')


def refresh_checksum(payload: bytes) -> bytes:
    bounds = _footer(payload)
    if bounds is None:
        raise ValueError('Unrecognized or missing FFWT checksum footer; refusing to edit.')
    start, _end = bounds
    checksum = zlib.crc32(payload[:start]) & 0xffffffff
    return payload[:start+12] + struct.pack('<I', checksum) + payload[start+16:]
