# Conformance Profile

## Strict baseline

A conforming run of this repository's strict baseline requires:

- deterministic `REFCANON-1` canonicalization;
- SHA-256 act digest;
- sink-local reconstruction/recomputation of live arguments digest;
- integrity-protected Execution Handle;
- expiry check;
- sink binding;
- current generation vector;
- explicit revocation check;
- exact-act digest match for `SINGLE_USE` and `COUNTED`;
- protected reuse state;
- verify and consume inside the same serialized local transaction;
- fail closed on consume-state loss;
- Finality Receipt not usable as authority.

## `REFCANON-1`

Canonical form is UTF-8 JSON with recursively sorted object keys and no insignificant whitespace. Floats are forbidden. Python accepts signed 64-bit integers. Shared Python/Node/Go vectors use only integers that all three can represent exactly.

The profile is deliberately narrow and should not be mislabeled as full JCS.

## Reuse semantics

### SINGLE_USE

`uses == 0` is required before commit; transaction sets `uses = 1` and inserts the effect.

### COUNTED

`uses < max_uses` is required; transaction increments `uses` and commits. The reference effect table's unique candidate ID is a local implementation constraint. Real counted profiles must define what distinguishes each effect while preserving the intended authorization semantics.

### ENVELOPE

Base-draft ENVELOPE effectuation is rejected with `EF-042` unless an explicit binding profile is selected. `EH-REF-ENVELOPE-1` is an experimental profile whose digest binds the invariant fields and the envelope text; full live digests are stored for replay detection.

## Authority-object rule

`present_authority_object()` accepts only an `ExecutionHandle`. Finality receipts, attestation-shaped objects, SCITT-shaped receipts, and arbitrary token strings fail `EF-002`.

## Current test count

`tests/test_reference.py` contains 36 tests. `scripts/profile_matrix.py` adds 12 profile/concurrency matrix cases. Test count is not itself a security metric; the important property is whether the tests correspond to distinct failure modes and can be independently reproduced.
