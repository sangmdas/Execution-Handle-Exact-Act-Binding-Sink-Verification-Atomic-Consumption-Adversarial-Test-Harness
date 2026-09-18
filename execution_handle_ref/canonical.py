from __future__ import annotations
import hashlib
import json
from typing import Any

PROFILE = "REFCANON-1"

class CanonicalizationError(ValueError):
    pass

def _validate(v: Any, path: str = "$") -> None:
    if v is None or isinstance(v, (str, bool)):
        return
    # bool is subclass of int, so check bool first.
    if isinstance(v, int):
        if v < -(2**63) or v > 2**63 - 1:
            raise CanonicalizationError(f"integer out of signed-64 range at {path}")
        return
    if isinstance(v, float):
        raise CanonicalizationError(f"floats forbidden by {PROFILE} at {path}")
    if isinstance(v, list):
        for i, item in enumerate(v):
            _validate(item, f"{path}[{i}]")
        return
    if isinstance(v, dict):
        for k, item in v.items():
            if not isinstance(k, str):
                raise CanonicalizationError(f"non-string key at {path}")
            _validate(item, f"{path}.{k}")
        return
    raise CanonicalizationError(f"unsupported type {type(v).__name__} at {path}")

def canonical_bytes(v: Any) -> bytes:
    """Deterministic JSON profile used only by this reference implementation.

    Rules: UTF-8, recursively sorted object keys, no insignificant whitespace,
    Unicode emitted directly, integers limited to signed 64-bit, floats forbidden.
    It is intentionally narrower than full JCS to keep cross-language behavior obvious.
    """
    _validate(v)
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

def sha256_hex(v: Any) -> str:
    return hashlib.sha256(canonical_bytes(v)).hexdigest()

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
