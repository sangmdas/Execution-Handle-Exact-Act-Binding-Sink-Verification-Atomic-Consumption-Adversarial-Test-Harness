# Mapping from Draft Concepts to Executable Tests

This is a review aid, not a claim of normative IETF conformance.

| Draft concept | Implementation | Primary tests |
|---|---|---|
| Candidate Act + load-bearing digest | `cad.py` | 03, 11, 27, 28, 30 |
| Sink reconstruction | `ReferenceEngine.reconstruct()` | 11, 30 |
| Handle integrity | `_verify_integrity()` | 07, 34 |
| Exact-act binding | `_verify_inside()` | 03, 04, 23 |
| Sink binding | `_verify_inside()` | 05 |
| Expiry | `_verify_inside()` | 06 |
| Current generations | `_verify_inside()` | 08 |
| Revocation at commit time | `_verify_inside()` inside transaction | 09, 10 |
| SINGLE_USE | protected `handle_state` | 01, 02, 17, 18 |
| COUNTED | protected `handle_state` | 12, 35 |
| ENVELOPE replay default | experimental `EH-REF-ENVELOPE-1` | 13–16, 36 |
| Atomic consume + local commit | SQLite transaction | 17, 18, 19 |
| Receipt is evidence, not authority | `present_authority_object()` | 20 |
| Adjacent evidence is not authority | `present_authority_object()` | 21, 22, 33 |
| Optional workload key binding | `crypto.py` + `_verify_inside()` | 23–25 |
| Fail closed on store outage | `StoreUnavailable` → `EF-081` | 26 |
| Path completeness is required | explicit bypass demonstration | 31 |
| Policy correctness is not guaranteed | bad-policy-choice demonstration | 32 |

## One deliberate divergence

The base draft's ENVELOPE semantics need an additional binding definition to reconcile non-identical repeated acts with a single exact `act_digest`. The repository makes that uncertainty executable instead of hiding it: base ENVELOPE use fails; experimental `EH-REF-ENVELOPE-1` supplies one possible binding rule.
