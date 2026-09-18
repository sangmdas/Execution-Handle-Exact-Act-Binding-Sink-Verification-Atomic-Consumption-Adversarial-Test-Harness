from __future__ import annotations
import secrets
import time
import uuid
from typing import Any
from .canonical import sha256_hex
from .models import CandidateAct

LOAD_BEARING_FIELDS = (
    "version", "object_type", "candidate_act_id", "act_type", "consequence_class",
    "created_at", "expires_at", "actor", "operation", "arguments_digest", "destination",
    "purpose", "jurisdiction_policy_id", "finality_sink", "policy_generation",
    "freshness_nonce", "parent_act_id", "extensions",
)

def arguments_digest(arguments: dict[str, Any]) -> str:
    return sha256_hex(arguments)

def make_cad(*, act_type: str, consequence_class: str, actor: str, operation: str,
             arguments: dict[str, Any], destination: str, finality_sink: str,
             policy_generation: int, purpose: str | None = None,
             jurisdiction_policy_id: str | None = None, ttl_s: int = 300,
             now: int | None = None, candidate_act_id: str | None = None,
             freshness_nonce: str | None = None,
             parent_act_id: str | None = None,
             extensions: dict[str, Any] | None = None) -> CandidateAct:
    now = int(time.time()) if now is None else int(now)
    return CandidateAct(
        version="1.0", object_type="candidate_act",
        candidate_act_id=candidate_act_id or str(uuid.uuid4()),
        act_type=act_type, consequence_class=consequence_class,
        created_at=now, expires_at=now + ttl_s, actor=actor, operation=operation,
        arguments=dict(arguments), arguments_digest=arguments_digest(arguments),
        destination=destination, purpose=purpose,
        jurisdiction_policy_id=jurisdiction_policy_id, finality_sink=finality_sink,
        policy_generation=policy_generation,
        freshness_nonce=freshness_nonce or secrets.token_hex(16),
        parent_act_id=parent_act_id, extensions=extensions or {},
    )

def load_bearing(cad: CandidateAct) -> dict[str, Any]:
    d = cad.full_dict()
    # Raw arguments are not directly digested here; arguments_digest is load-bearing.
    d.pop("arguments", None)
    return {k: d[k] for k in LOAD_BEARING_FIELDS}

def act_digest(cad: CandidateAct) -> str:
    # Defense in depth: ensure the cached arguments_digest corresponds to live arguments.
    if cad.arguments_digest != arguments_digest(cad.arguments):
        # Return a digest that cannot silently validate a tampered in-memory CAD.
        # Sink verification emits EF-023 before relying on it.
        return "INVALID-ARGUMENT-DIGEST"
    return sha256_hex(load_bearing(cad))

def same_except(c1: CandidateAct, c2: CandidateAct, field: str) -> bool:
    d1, d2 = c1.full_dict(), c2.full_dict()
    d1.pop(field, None); d2.pop(field, None)
    return d1 == d2
