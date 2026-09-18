from __future__ import annotations
import json
import time
import uuid
from dataclasses import replace
from typing import Any, Callable
from .cad import act_digest, make_cad, arguments_digest
from .canonical import PROFILE
from .crypto import mac_hex, verify_mac, verify_pop
from .errors import *
from .models import CandidateAct, ExecutionHandle, FinalityReceipt
from .store import SQLiteStore, StoreUnavailable

class ReferenceEngine:
    def __init__(self, store: SQLiteStore, *, sink_id: str, issuer_id: str = "ped-ref",
                 issuer_key: bytes = b"dev-issuer-key-change-me",
                 sink_key: bytes = b"dev-sink-key-change-me",
                 workload_keys: dict[str, bytes] | None = None,
                 clock: Callable[[], int] | None = None):
        self.store = store
        self.sink_id = sink_id
        self.issuer_id = issuer_id
        self.issuer_key = issuer_key
        self.sink_key = sink_key
        self.workload_keys = workload_keys or {}
        self.clock = clock or (lambda: int(time.time()))

    def issue(self, cad: CandidateAct, *, reuse_policy: str = "SINGLE_USE", max_uses: int | None = None,
              envelope: dict[str, Any] | None = None, key_binding: str | None = None,
              ttl_s: int = 300) -> ExecutionHandle:
        now = self.clock()
        if cad.expires_at <= now:
            raise EFError(EF004, "candidate act expired before issuance")
        if cad.arguments_digest != arguments_digest(cad.arguments):
            raise EFError(EF003, "candidate act arguments digest invalid")
        if reuse_policy not in ("SINGLE_USE", "COUNTED", "ENVELOPE"):
            raise EFError(EF042, "unsupported reuse policy")
        if reuse_policy == "COUNTED" and (not max_uses or max_uses < 1):
            raise EFError(EF042, "COUNTED requires max_uses >= 1")
        if reuse_policy == "ENVELOPE" and not envelope:
            raise EFError(EF042, "ENVELOPE requires explicit envelope")

        generations = self.store.generation_vector()
        eh = ExecutionHandle(
            version="1.0", object_type="execution_handle", handle_id=str(uuid.uuid4()),
            issuer=self.issuer_id, issued_at=now, expires_at=min(cad.expires_at, now + ttl_s),
            act_digest=act_digest(cad), candidate_act_id=cad.candidate_act_id,
            finality_sink_id=cad.finality_sink, reuse_policy=reuse_policy, max_uses=max_uses,
            envelope=envelope, generations=generations, confirmation_method="sink_reconstruction",
            not_bearer_alone=True, key_binding=key_binding, canonical_profile=PROFILE,
            extensions={},
        )
        eh.signature = mac_hex(eh.unsigned_dict(), self.issuer_key)
        return eh

    def _verify_integrity(self, eh: ExecutionHandle):
        if eh.object_type != "execution_handle" or not verify_mac(eh.unsigned_dict(), eh.signature, self.issuer_key):
            raise EFError(EF003, "execution handle integrity failure")
        if not eh.not_bearer_alone:
            raise EFError(EF012, "strict profile requires not_bearer_alone=true")
        if eh.canonical_profile != PROFILE:
            raise EFError(EF012, "unsupported canonicalization profile")

    def reconstruct(self, observed: CandidateAct) -> CandidateAct:
        # In this reference harness, `observed` represents sink-local fields immediately before
        # effectuation. Recompute arguments_digest so a stale caller digest cannot override them.
        return replace(observed, arguments_digest=arguments_digest(observed.arguments))

    def _check_envelope(self, cad: CandidateAct, envelope: dict[str, Any]) -> bool:
        # Experimental EH-REF-ENVELOPE-1 constraints. Not claimed as the base draft's missing
        # wire rule. Only explicitly listed fields can vary; everything else remains exact.
        constraints = envelope.get("constraints", {})
        for path, rule in constraints.items():
            if path.startswith("arguments."):
                key = path.split(".", 1)[1]; value = cad.arguments.get(key)
            elif path == "destination": value = cad.destination
            elif path == "operation": value = cad.operation
            else: return False
            if "eq" in rule and value != rule["eq"]: return False
            if "one_of" in rule and value not in rule["one_of"]: return False
            if "min" in rule and (not isinstance(value, int) or value < rule["min"]): return False
            if "max" in rule and (not isinstance(value, int) or value > rule["max"]): return False
        return True

    def _envelope_binding_digest(self, cad: CandidateAct, envelope: dict[str, Any]) -> str:
        # Bind invariant fields plus the textual envelope constraints. This is the explicit
        # experimental rule that resolves the draft's non-identical-reuse ambiguity.
        from .canonical import sha256_hex
        variable = set(envelope.get("constraints", {}).keys())
        args = dict(cad.arguments)
        for p in list(variable):
            if p.startswith("arguments."):
                args.pop(p.split(".",1)[1], None)
        fixed = {
            "version": cad.version, "object_type": cad.object_type,
            "act_type": cad.act_type, "consequence_class": cad.consequence_class,
            "actor": cad.actor, "operation": None if "operation" in variable else cad.operation,
            "arguments_fixed": args,
            "destination": None if "destination" in variable else cad.destination,
            "purpose": cad.purpose, "jurisdiction_policy_id": cad.jurisdiction_policy_id,
            "finality_sink": cad.finality_sink, "policy_generation": cad.policy_generation,
            "parent_act_id": cad.parent_act_id, "envelope": envelope,
        }
        return sha256_hex(fixed)

    def issue_envelope(self, cad: CandidateAct, *, envelope: dict[str, Any], key_binding: str | None = None,
                       ttl_s: int = 300) -> ExecutionHandle:
        eh = self.issue(cad, reuse_policy="ENVELOPE", envelope=envelope, key_binding=key_binding, ttl_s=ttl_s)
        eh.act_digest = self._envelope_binding_digest(cad, envelope)
        eh.extensions = {"profile": "EH-REF-ENVELOPE-1"}
        eh.signature = mac_hex(eh.unsigned_dict(), self.issuer_key)
        return eh

    def early_verify_hint(self, observed: CandidateAct, eh: ExecutionHandle, *, pop: str | None = None) -> bool:
        # Deliberately non-authoritative. Used to demonstrate why re-check at commit is mandatory.
        self._verify_integrity(eh)
        cad = self.reconstruct(observed)
        if eh.finality_sink_id != self.sink_id: raise EFError(EF040, "sink mismatch")
        if eh.expires_at <= self.clock(): raise EFError(EF004, "handle expired")
        if eh.reuse_policy != "ENVELOPE" and act_digest(cad) != eh.act_digest:
            if cad.destination != observed.destination: raise EFError(EF020, "destination mismatch")
            raise EFError(EF023, "act digest mismatch")
        return True

    def _verify_inside(self, c, cad: CandidateAct, eh: ExecutionHandle, pop: str | None):
        self._verify_integrity(eh)
        now = self.clock()
        if eh.expires_at <= now: raise EFError(EF004, "handle expired")
        if eh.finality_sink_id != self.sink_id or cad.finality_sink != self.sink_id:
            raise EFError(EF040, "sink mismatch")
        if self.store.is_revoked(eh.handle_id, c):
            raise EFError(EF062, "handle revoked")
        current = self.store.generation_vector(c)
        for name, issued in eh.generations.items():
            if current.get(name) != issued:
                # A specific revoked row gets EF-062 above; other generation drift is EF-041.
                raise EFError(EF041, f"generation stale: {name}")
        if cad.policy_generation != current.get("policy"):
            raise EFError(EF041, "CAD policy generation stale")
        if eh.key_binding:
            key = self.workload_keys.get(eh.key_binding)
            if not key or not pop or not verify_pop(eh.handle_id, act_digest(cad), self.sink_id, pop, key):
                raise EFError(EF012, "required workload proof-of-possession failed")
        if eh.reuse_policy == "ENVELOPE":
            if eh.extensions.get("profile") != "EH-REF-ENVELOPE-1":
                raise EFError(EF042, "base draft ENVELOPE binding is underspecified; explicit profile required")
            if not self._check_envelope(cad, eh.envelope or {}):
                raise EFError(EF043, "live act outside envelope")
            if self._envelope_binding_digest(cad, eh.envelope or {}) != eh.act_digest:
                raise EFError(EF023, "envelope invariant binding mismatch")
        else:
            live_digest = act_digest(cad)
            if live_digest != eh.act_digest:
                # Emit the more specific destination code when an otherwise identical issuance
                # context differs only at destination is not always recoverable from EH alone;
                # the profile uses EF-020 when candidate IDs match and destination is flagged.
                if cad.candidate_act_id == eh.candidate_act_id and cad.extensions.get("mutation") == "destination":
                    raise EFError(EF020, "destination mismatch")
                raise EFError(EF023, "act digest mismatch")
        return current

    def consume_and_commit(self, observed: CandidateAct, eh: ExecutionHandle, *, pop: str | None = None,
                           payload: dict[str, Any] | None = None,
                           inside_hook: Callable[[Any], None] | None = None,
                           crash_point: str | None = None) -> FinalityReceipt:
        try:
            with self.store.atomic() as c:
                cad = self.reconstruct(observed)
                if inside_hook:
                    inside_hook(c)
                current = self._verify_inside(c, cad, eh, pop)
                uses, used_digests = self.store.get_state(eh.handle_id, c)
                live_digest = act_digest(cad)
                if eh.reuse_policy == "SINGLE_USE":
                    if uses >= 1: raise EFError(EF005, "single-use authority already consumed")
                    uses = 1
                elif eh.reuse_policy == "COUNTED":
                    if eh.max_uses is None or uses >= eh.max_uses:
                        raise EFError(EF005, "counted authority exhausted")
                    uses += 1
                elif eh.reuse_policy == "ENVELOPE":
                    if live_digest in used_digests and not (eh.envelope or {}).get("allow_identical_replay", False):
                        raise EFError(EF006, "identical envelope replay detected")
                    uses += 1; used_digests.add(live_digest)
                else:
                    raise EFError(EF042, "unknown reuse policy")
                self.store.put_state(eh.handle_id, uses, used_digests, c)
                if crash_point == "after_consume_before_commit":
                    raise RuntimeError("SIMULATED_CRASH_AFTER_CONSUME")
                # Reconfirm the exact observed effect has not changed in this reference object.
                if cad.arguments_digest != arguments_digest(cad.arguments):
                    raise EFError(EF023, "arguments changed before protected commit")
                c.execute("INSERT INTO effects(candidate_act_id,handle_id,act_digest,payload,committed_at) VALUES (?,?,?,?,?)",
                          (cad.candidate_act_id, eh.handle_id, live_digest, json.dumps(payload or cad.full_dict(), sort_keys=True), self.clock()))
                if crash_point == "after_commit_before_response":
                    # Transaction will roll back in this local atomic model. A real remote effect
                    # cannot be rolled back this way; see LIMITATIONS.md and outbox guidance.
                    raise RuntimeError("SIMULATED_CRASH_AFTER_COMMIT_BEFORE_RESPONSE")
                receipt = self._receipt(eh, cad, "EFFECTUATED", "CONSUMED", None, current)
                c.execute("INSERT INTO receipts(receipt_id,payload) VALUES (?,?)", (receipt.receipt_id, json.dumps(receipt.__dict__, sort_keys=True)))
                return receipt
        except StoreUnavailable as e:
            raise EFError(EF081, str(e)) from e

    def _receipt(self, eh, cad, decision, outcome, reason, generations) -> FinalityReceipt:
        unsigned = {
            "object_type": "finality_receipt", "receipt_id": str(uuid.uuid4()),
            "sink_id": self.sink_id, "handle_id": eh.handle_id,
            "candidate_act_id": cad.candidate_act_id, "act_digest": act_digest(cad),
            "decision": decision, "consume_outcome": outcome, "reason_code": reason,
            "generations_observed": generations, "issued_at": self.clock(),
        }
        return FinalityReceipt(**unsigned, signature=mac_hex(unsigned, self.sink_key))

    def present_authority_object(self, observed: CandidateAct, obj: Any):
        if not isinstance(obj, ExecutionHandle):
            raise EFError(EF002, "object is not execution-finality authority")
        return self.consume_and_commit(observed, obj)
