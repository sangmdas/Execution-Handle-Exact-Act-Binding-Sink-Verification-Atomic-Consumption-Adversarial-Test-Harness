from __future__ import annotations
import hmac
import hashlib
from .canonical import canonical_bytes

# HMAC is intentionally used for the zero-dependency reference profile.
# Production deployments should select a key-management and signature/MAC profile appropriate
# to their trust domain; this module is not a PKI recommendation.

def mac_hex(obj: dict, key: bytes) -> str:
    return hmac.new(key, canonical_bytes(obj), hashlib.sha256).hexdigest()

def verify_mac(obj: dict, signature: str, key: bytes) -> bool:
    return hmac.compare_digest(mac_hex(obj, key), signature)

def pop_proof(handle_id: str, act_digest: str, sink_id: str, key: bytes) -> str:
    msg = f"{handle_id}\n{act_digest}\n{sink_id}".encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()

def verify_pop(handle_id: str, act_digest: str, sink_id: str, proof: str, key: bytes) -> bool:
    return hmac.compare_digest(pop_proof(handle_id, act_digest, sink_id, key), proof)
