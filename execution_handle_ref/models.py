from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Literal

ReusePolicy = Literal["SINGLE_USE", "COUNTED", "ENVELOPE"]

@dataclass(frozen=True)
class CandidateAct:
    version: str
    object_type: str
    candidate_act_id: str
    act_type: str
    consequence_class: str
    created_at: int
    expires_at: int
    actor: str
    operation: str
    arguments: dict[str, Any]
    arguments_digest: str
    destination: str
    purpose: str | None
    jurisdiction_policy_id: str | None
    finality_sink: str
    policy_generation: int
    freshness_nonce: str
    parent_act_id: str | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    def full_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass
class ExecutionHandle:
    version: str
    object_type: str
    handle_id: str
    issuer: str
    issued_at: int
    expires_at: int
    act_digest: str
    candidate_act_id: str
    finality_sink_id: str
    reuse_policy: ReusePolicy
    max_uses: int | None
    envelope: dict[str, Any] | None
    generations: dict[str, int]
    confirmation_method: str
    not_bearer_alone: bool
    key_binding: str | None
    canonical_profile: str
    signature: str = ""
    extensions: dict[str, Any] = field(default_factory=dict)

    def unsigned_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("signature", None)
        return d

    def full_dict(self) -> dict[str, Any]:
        return asdict(self)

@dataclass(frozen=True)
class FinalityReceipt:
    object_type: str
    receipt_id: str
    sink_id: str
    handle_id: str
    candidate_act_id: str
    act_digest: str
    decision: str
    consume_outcome: str
    reason_code: str | None
    generations_observed: dict[str, int]
    issued_at: int
    signature: str
