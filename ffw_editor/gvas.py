"""
Minimal UE5 GVAS save-game parser/serializer for FarFarWest saves.

The decrypted file is a normal GVAS container, but the property tags used by
this game are not the older stock layout of:

    name, type, int64 size, int32 array_index, type-header, terminator, value

FarFarWest serializes:

    name, type, type-descriptor, int32 value_size, uint8 terminator, value

The descriptor records property metadata such as struct/enum paths. We parse it
enough to expose readable values, and preserve the raw descriptor bytes so a
parse -> serialize round trip can stay byte-identical.
"""
from __future__ import annotations

import base64
import io
import struct
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Low-level read/write primitives
# ---------------------------------------------------------------------------
class Reader:
    def __init__(self, buf: bytes):
        self.b = memoryview(buf)
        self.p = 0

    def read(self, n: int) -> bytes:
        if n < 0:
            raise ValueError(f"negative read length {n}")
        if self.p + n > len(self.b):
            raise EOFError(f"read past end (need {n}, have {len(self.b) - self.p})")
        out = bytes(self.b[self.p : self.p + n])
        self.p += n
        return out

    def i8(self):  return struct.unpack("<b", self.read(1))[0]
    def u8(self):  return self.read(1)[0]
    def i16(self): return struct.unpack("<h", self.read(2))[0]
    def u16(self): return struct.unpack("<H", self.read(2))[0]
    def i32(self): return struct.unpack("<i", self.read(4))[0]
    def u32(self): return struct.unpack("<I", self.read(4))[0]
    def i64(self): return struct.unpack("<q", self.read(8))[0]
    def u64(self): return struct.unpack("<Q", self.read(8))[0]
    def f32(self): return struct.unpack("<f", self.read(4))[0]
    def f64(self): return struct.unpack("<d", self.read(8))[0]

    def guid(self) -> str:
        return self.read(16).hex()

    def fstring(self) -> str:
        n = self.i32()
        if n == 0:
            return ""
        if n > 0:
            data = self.read(n)
            if data.endswith(b"\x00"):
                data = data[:-1]
            return data.decode("utf-8", errors="replace")
        n = -n
        data = self.read(n * 2)
        if data.endswith(b"\x00\x00"):
            data = data[:-2]
        return data.decode("utf-16-le", errors="replace")

    def plausible_fstring_at(self, pos: int) -> bool:
        if pos < 0 or pos + 4 > len(self.b):
            return False
        # Check if this position starts with a null byte - if so, not a valid fstring
        # (this is the special separator byte that appears in some saves)
        if self.b[pos] == 0:
            return False
        n = struct.unpack_from("<i", self.b, pos)[0]
        if n == 0:
            return True
        if n > 0:
            if n > 4096 or pos + 4 + n > len(self.b):
                return False
            data = bytes(self.b[pos + 4 : pos + 4 + n])
            return data.endswith(b"\x00")
        n = -n
        return n <= 4096 and pos + 4 + n * 2 <= len(self.b)


class Writer:
    def __init__(self):
        self.io = io.BytesIO()

    def getvalue(self) -> bytes:
        return self.io.getvalue()

    def write(self, b: bytes): self.io.write(b)
    def i8(self, v):  self.io.write(struct.pack("<b", v))
    def u8(self, v):  self.io.write(struct.pack("<B", v))
    def i16(self, v): self.io.write(struct.pack("<h", v))
    def u16(self, v): self.io.write(struct.pack("<H", v))
    def i32(self, v): self.io.write(struct.pack("<i", v))
    def u32(self, v): self.io.write(struct.pack("<I", v))
    def i64(self, v): self.io.write(struct.pack("<q", v))
    def u64(self, v): self.io.write(struct.pack("<Q", v))
    def f32(self, v): self.io.write(struct.pack("<f", v))
    def f64(self, v): self.io.write(struct.pack("<d", v))

    def guid(self, hex32: str):
        if len(hex32) != 32:
            raise ValueError("guid must be 32 hex chars")
        self.io.write(bytes.fromhex(hex32))

    def fstring(self, s: str):
        if s == "":
            self.i32(0)
            return
        try:
            data = s.encode("ascii") + b"\x00"
            self.i32(len(data))
            self.io.write(data)
        except UnicodeEncodeError:
            data = s.encode("utf-16-le") + b"\x00\x00"
            self.i32(-(len(data) // 2))
            self.io.write(data)


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"))


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
@dataclass
class CustomVersion:
    guid: str
    version: int


@dataclass
class GvasHeader:
    save_game_file_version: int
    package_file_ue4_version: int
    package_file_ue5_version: int | None
    engine_version_major: int
    engine_version_minor: int
    engine_version_patch: int
    engine_version_changelist: int
    engine_version_branch: str
    custom_versions_format: int
    custom_versions: list[CustomVersion] = field(default_factory=list)
    save_game_class_name: str = ""

    @classmethod
    def read(cls, r: Reader) -> "GvasHeader":
        magic = r.read(4)
        if magic != b"GVAS":
            raise ValueError(f"bad magic {magic!r}")
        sgfv = r.i32()
        pkg_ue4 = r.i32()
        pkg_ue5 = r.i32() if sgfv >= 3 else None
        major = r.i16()
        minor = r.i16()
        patch = r.i16()
        changelist = r.i32()
        branch = r.fstring()
        cv_fmt = r.i32()
        n = r.i32()
        cvs = [CustomVersion(r.guid(), r.i32()) for _ in range(n)]
        sgcn = r.fstring()
        return cls(
            sgfv, pkg_ue4, pkg_ue5, major, minor, patch, changelist,
            branch, cv_fmt, cvs, sgcn,
        )

    def write(self, w: Writer):
        w.write(b"GVAS")
        w.i32(self.save_game_file_version)
        w.i32(self.package_file_ue4_version)
        if self.save_game_file_version >= 3:
            w.i32(self.package_file_ue5_version or 0)
        w.i16(self.engine_version_major)
        w.i16(self.engine_version_minor)
        w.i16(self.engine_version_patch)
        w.i32(self.engine_version_changelist)
        w.fstring(self.engine_version_branch)
        w.i32(self.custom_versions_format)
        w.i32(len(self.custom_versions))
        for cv in self.custom_versions:
            w.guid(cv.guid)
            w.i32(cv.version)
        w.fstring(self.save_game_class_name)


# ---------------------------------------------------------------------------
# Property descriptors
# ---------------------------------------------------------------------------
def _read_type_meta(r: Reader, type_: str) -> dict[str, Any]:
    meta: dict[str, Any] = {"kind": r.i32()}

    if type_ == "StructProperty":
        meta["struct_type"] = r.fstring()
        meta["struct_path_flag"] = r.i32()
        meta["struct_path"] = r.fstring()
        meta["struct_unknown"] = r.i32()
        meta["struct_guid"] = r.fstring()
        meta["struct_tail"] = r.i32()
        return meta

    if type_ == "ByteProperty":
        meta["enum_type"] = r.fstring()
        meta["enum_path_flag"] = r.i32()
        meta["enum_path"] = r.fstring()
        meta["enum_tail"] = r.i32()
        return meta

    if type_ == "ArrayProperty":
        meta["inner_type"] = r.fstring()
        meta["inner_meta"] = _read_type_meta(r, meta["inner_type"])
        return meta

    if type_ == "MapProperty":
        meta["key_type"] = r.fstring()
        meta["key_meta"] = _read_type_meta(r, meta["key_type"])
        meta["value_type"] = r.fstring()
        meta["value_meta"] = _read_type_meta(r, meta["value_type"])
        return meta

    if type_ == "SetProperty":
        meta["inner_type"] = r.fstring()
        meta["inner_meta"] = _read_type_meta(r, meta["inner_type"])
        return meta

    # For all other property types (NameProperty, IntProperty, etc.)
    # FarFarWest format has no additional metadata after "kind"
    # Just return the kind we already read
    return meta


def _read_property(r: Reader, name: str) -> dict[str, Any]:
    type_ = r.fstring()
    meta_start = r.p
    meta = _read_type_meta(r, type_)
    meta_raw = bytes(r.b[meta_start:r.p])
    size = r.i32()
    terminator = r.u8()
    if terminator != 0:
        raise ValueError(f"expected 0 terminator for {name}, got {terminator}")

    value_start = r.p
    value_end = value_start + size
    if value_end > len(r.b):
        raise EOFError(f"property {name} value overruns file (need {size}, have {len(r.b) - r.p})")

    raw_bytes = bytes(r.b[value_start:value_end])
    p: dict[str, Any] = {
        "_name": name,
        "_type": type_,
        "_format": "ffw",
        "_size": size,
        "_meta": meta,
        "_meta_raw": _b64(meta_raw),
        "_raw_value": _b64(raw_bytes),
    }
    _flatten_meta(p, meta)

    try:
        p["value"] = _read_value(r, type_, meta, size)
    except Exception as exc:
        r.p = value_start
        p["_raw"] = _b64(r.read(size))
        p["_parse_error"] = str(exc)
        return p

    if r.p < value_end:
        p["_value_trailing"] = _b64(r.read(value_end - r.p))
    elif r.p > value_end:
        raise ValueError(f"property {name} consumed past declared size")
    return p


def _flatten_meta(p: dict[str, Any], meta: dict[str, Any]) -> None:
    if "struct_type" in meta:
        p["struct_type"] = meta["struct_type"]
        p["struct_path"] = meta["struct_path"]
        p["struct_guid"] = meta["struct_guid"]
    if "enum_type" in meta:
        p["enum"] = meta["enum_type"]
        p["enum_path"] = meta["enum_path"]
    if "inner_type" in meta:
        p["inner_type"] = meta["inner_type"]
    if "key_type" in meta:
        p["key_type"] = meta["key_type"]
        p["value_type"] = meta["value_type"]


# ---------------------------------------------------------------------------
# Property values
# ---------------------------------------------------------------------------
def _read_value(r: Reader, type_: str, meta: dict[str, Any], size: int) -> Any:
    if type_ == "BoolProperty":
        return r.u8() != 0
    if type_ == "ByteProperty":
        if size == 1:
            return r.u8()
        return r.fstring()
    if type_ == "EnumProperty":
        return r.fstring()
    if type_ == "StructProperty":
        return _read_struct_value(r, meta.get("struct_type", ""), size)
    if type_ == "ArrayProperty":
        return _read_array_value(r, meta["inner_type"], meta["inner_meta"], size)
    if type_ == "MapProperty":
        return _read_map_value(r, meta["key_type"], meta["key_meta"], meta["value_type"], meta["value_meta"])
    if type_ == "SetProperty":
        removed = r.i32()
        n = r.i32()
        return {
            "num_keys_to_remove": removed,
            "items": [_read_inline_value(r, meta["inner_type"], meta["inner_meta"]) for _ in range(n)],
        }
    if type_ == "IntProperty":
        return r.i32()
    if type_ == "Int64Property":
        return r.i64()
    if type_ == "UInt32Property":
        return r.u32()
    if type_ == "UInt64Property":
        return r.u64()
    if type_ == "FloatProperty":
        return r.f32()
    if type_ == "DoubleProperty":
        return r.f64()
    if type_ in ("StrProperty", "NameProperty", "ObjectProperty"):
        return r.fstring()
    if type_ == "SoftObjectProperty":
        return {"asset": r.fstring(), "sub_path": r.fstring()}
    return {"_raw": _b64(r.read(size))}


def _read_struct_value(r: Reader, struct_type: str, size: int) -> Any:
    if struct_type in ("Vector", "Vector3f"):
        return {"x": r.f32(), "y": r.f32(), "z": r.f32()} if size == 12 else {"x": r.f64(), "y": r.f64(), "z": r.f64()}
    if struct_type in ("Rotator", "Rotator3f"):
        return {"pitch": r.f32(), "yaw": r.f32(), "roll": r.f32()} if size == 12 else {"pitch": r.f64(), "yaw": r.f64(), "roll": r.f64()}
    if struct_type in ("Quat", "Quat4f"):
        return {"x": r.f32(), "y": r.f32(), "z": r.f32(), "w": r.f32()} if size == 16 else {"x": r.f64(), "y": r.f64(), "z": r.f64(), "w": r.f64()}
    if struct_type == "Color":
        return {"b": r.u8(), "g": r.u8(), "r": r.u8(), "a": r.u8()}
    if struct_type == "LinearColor":
        return {"r": r.f32(), "g": r.f32(), "b": r.f32(), "a": r.f32()}
    if struct_type == "Guid":
        return r.guid()
    if struct_type in ("DateTime", "Timespan"):
        return r.i64()
    if struct_type == "IntPoint":
        return {"x": r.i32(), "y": r.i32()}
    return _read_properties(r)


def _read_array_value(r: Reader, inner_type: str, inner_meta: dict[str, Any], size: int) -> Any:
    n = r.i32()
    return [_read_inline_value(r, inner_type, inner_meta) for _ in range(n)]


def _read_map_value(
    r: Reader,
    key_type: str,
    key_meta: dict[str, Any],
    value_type: str,
    value_meta: dict[str, Any],
) -> dict[str, Any]:
    removed = r.i32()
    n = r.i32()
    items = []
    for _ in range(n):
        items.append({
            "key": _read_inline_value(r, key_type, key_meta),
            "value": _read_inline_value(r, value_type, value_meta),
        })
    return {"num_keys_to_remove": removed, "items": items}


def _read_inline_value(r: Reader, type_: str, meta: dict[str, Any]) -> Any:
    if type_ == "BoolProperty":
        return r.u8() != 0
    if type_ == "ByteProperty":
        return r.u8()
    if type_ == "IntProperty":
        return r.i32()
    if type_ == "Int64Property":
        return r.i64()
    if type_ == "UInt32Property":
        return r.u32()
    if type_ == "UInt64Property":
        return r.u64()
    if type_ == "FloatProperty":
        return r.f32()
    if type_ == "DoubleProperty":
        return r.f64()
    if type_ in ("StrProperty", "NameProperty", "EnumProperty", "ObjectProperty"):
        return r.fstring()
    if type_ == "SoftObjectProperty":
        return {"asset": r.fstring(), "sub_path": r.fstring()}
    if type_ == "StructProperty":
        return _read_struct_value(r, meta.get("struct_type", ""), 0)
    raise NotImplementedError(f"inline read for {type_}")


def _read_properties(r: Reader) -> list[dict[str, Any]]:
    out = []
    while True:
        name = r.fstring()
        if name == "None":
            break
        out.append(_read_property(r, name))
    return out


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------
def _write_properties(w: Writer, props: list[dict[str, Any]]):
    for p in props:
        w.fstring(p["_name"])
        _write_property(w, p)
    w.fstring("None")


def _write_property(w: Writer, p: dict[str, Any]):
    type_ = p["_type"]
    w.fstring(type_)
    value = _write_value_bytes(p)
    w.write(_unb64(p["_meta_raw"]))
    w.i32(len(value))
    w.u8(0)
    w.write(value)


def _write_value_bytes(p: dict[str, Any]) -> bytes:
    if "_raw" in p:
        return _unb64(p["_raw"])
    if p.get("_type") == "IntProperty" and "_raw_value" in p:
        raw = bytearray(_unb64(p["_raw_value"]))
        if len(raw) >= 4:
            raw[:4] = struct.pack("<i", int(p["value"]))
            return bytes(raw)
    w = Writer()
    _write_value(w, p["_type"], p.get("_meta", {}), p["value"])
    if "_value_trailing" in p:
        w.write(_unb64(p["_value_trailing"]))
    return w.getvalue()


def _write_value(w: Writer, type_: str, meta: dict[str, Any], value: Any):
    if type_ == "BoolProperty":
        w.u8(1 if value else 0)
    elif type_ == "ByteProperty":
        if isinstance(value, int):
            w.u8(value)
        else:
            w.fstring(value)
    elif type_ == "EnumProperty":
        w.fstring(value)
    elif type_ == "StructProperty":
        _write_struct_value(w, meta.get("struct_type", ""), value)
    elif type_ == "ArrayProperty":
        w.i32(len(value))
        for item in value:
            _write_inline_value(w, meta["inner_type"], meta["inner_meta"], item)
    elif type_ == "MapProperty":
        w.i32(value.get("num_keys_to_remove", 0))
        w.i32(len(value["items"]))
        for item in value["items"]:
            _write_inline_value(w, meta["key_type"], meta["key_meta"], item["key"])
            _write_inline_value(w, meta["value_type"], meta["value_meta"], item["value"])
    elif type_ == "SetProperty":
        w.i32(value.get("num_keys_to_remove", 0))
        w.i32(len(value["items"]))
        for item in value["items"]:
            _write_inline_value(w, meta["inner_type"], meta["inner_meta"], item)
    elif type_ == "IntProperty":
        w.i32(int(value))
    elif type_ == "Int64Property":
        w.i64(int(value))
    elif type_ == "UInt32Property":
        w.u32(int(value))
    elif type_ == "UInt64Property":
        w.u64(int(value))
    elif type_ == "FloatProperty":
        w.f32(float(value))
    elif type_ == "DoubleProperty":
        w.f64(float(value))
    elif type_ in ("StrProperty", "NameProperty", "ObjectProperty"):
        w.fstring(value)
    elif type_ == "SoftObjectProperty":
        w.fstring(value["asset"])
        w.fstring(value.get("sub_path", ""))
    elif isinstance(value, dict) and "_raw" in value:
        w.write(_unb64(value["_raw"]))
    else:
        raise NotImplementedError(f"write {type_}")


def _write_struct_value(w: Writer, struct_type: str, value: Any):
    if struct_type in ("Vector", "Vector3f"):
        for k in "xyz":
            w.f32(value[k])
    elif struct_type in ("Rotator", "Rotator3f"):
        for k in ("pitch", "yaw", "roll"):
            w.f32(value[k])
    elif struct_type in ("Quat", "Quat4f"):
        for k in "xyzw":
            w.f32(value[k])
    elif struct_type == "Color":
        w.u8(value["b"]); w.u8(value["g"]); w.u8(value["r"]); w.u8(value["a"])
    elif struct_type == "LinearColor":
        for k in "rgba":
            w.f32(value[k])
    elif struct_type == "Guid":
        w.guid(value)
    elif struct_type in ("DateTime", "Timespan"):
        w.i64(value)
    elif struct_type == "IntPoint":
        w.i32(value["x"]); w.i32(value["y"])
    else:
        _write_properties(w, value)


def _write_inline_value(w: Writer, type_: str, meta: dict[str, Any], value: Any):
    if type_ == "BoolProperty":
        w.u8(1 if value else 0)
    elif type_ == "ByteProperty":
        w.u8(int(value))
    elif type_ == "IntProperty":
        w.i32(int(value))
    elif type_ == "Int64Property":
        w.i64(int(value))
    elif type_ == "UInt32Property":
        w.u32(int(value))
    elif type_ == "UInt64Property":
        w.u64(int(value))
    elif type_ == "FloatProperty":
        w.f32(float(value))
    elif type_ == "DoubleProperty":
        w.f64(float(value))
    elif type_ in ("StrProperty", "NameProperty", "EnumProperty", "ObjectProperty"):
        w.fstring(value)
    elif type_ == "SoftObjectProperty":
        w.fstring(value["asset"])
        w.fstring(value.get("sub_path", ""))
    elif type_ == "StructProperty":
        _write_struct_value(w, meta.get("struct_type", ""), value)
    else:
        raise NotImplementedError(f"inline write for {type_}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
@dataclass
class GvasFile:
    header: GvasHeader
    properties: list[dict[str, Any]]
    pre_properties: bytes = b""
    trailing: bytes = b""

    @classmethod
    def parse(cls, data: bytes) -> "GvasFile":
        r = Reader(data)
        header = GvasHeader.read(r)

        # This save has a single zero byte between the class name and the first
        # property tag. Preserve it instead of baking it into the header model.
        pre_properties = b""
        if not r.plausible_fstring_at(r.p) and r.p < len(r.b) and r.b[r.p] == 0 and r.plausible_fstring_at(r.p + 1):
            pre_properties = r.read(1)

        props = _read_properties(r)
        trailing = bytes(r.b[r.p:])
        return cls(header=header, properties=props, pre_properties=pre_properties, trailing=trailing)

    def serialize(self) -> bytes:
        w = Writer()
        self.header.write(w)
        w.write(self.pre_properties)
        _write_properties(w, self.properties)
        w.write(self.trailing)
        return w.getvalue()
