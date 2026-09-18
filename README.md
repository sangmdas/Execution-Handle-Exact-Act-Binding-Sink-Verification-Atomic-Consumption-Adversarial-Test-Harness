# Execution Handle — Runnable Reference Implementation and Adversarial Test Harness

**Reference target:** `draft-das-execution-handle-01` — *Possession Is Not Authority: Execution Handle, Sink Verification, Atomic Consumption, and Finality Receipt*

This repository turns the draft's central invariant into executable code:

> A valid object is not sufficient authority merely because it can be presented. The component that is about to make a consequence real reconstructs the live pending act, checks that the handle is bound to that exact act and that sink, checks current generations/revocation and optional key binding, atomically consumes the allowed reuse state, and only then commits the protected effect.

This is intentionally more than a happy-path demonstration. It includes negative tests, concurrency races, revocation timing, crash injection, canonicalization interop, fail-closed behavior, explicit bypass demonstrations, critic-facing limitations, and a documented ambiguity discovered while implementing `ENVELOPE` reuse.

## Status

This is a **reference/conformance implementation**, not production middleware, not a security certification, and not an assertion that the Internet-Draft is standardized. The illustrative `EF-*` codes are treated as draft-local codes; they are not represented as IANA assignments.

Current checked run in `results/`:

- **36/36** adversarial unit tests passed.
- **12/12** profile/variable matrix cases passed.
- A deterministic **2,000-case** mutation/canonicalization probe passed: equivalent key reordering preserved digests and each single-argument mutation changed the digest.
- Python, Node.js, and Go generated **identical SHA-256 digests** for the shared deterministic canonicalization vectors.
- `SINGLE_USE` races were exercised at **2, 8, 32, and 64 concurrent workers**; each run produced exactly one successful commit and `EF-005` for the remaining workers.
- Local durable SQLite benchmark, 1,000 independently issued and committed acts: about **1,041 end-to-end ops/s**; local protected commit p50 about **0.57 ms**, p95 about **0.70 ms**, p99 about **1.00 ms** on the recorded Linux x86_64 environment.

The benchmark is **not** a production latency claim. It excludes network latency, real payment rails, actuator buses, HSM/TEE calls, remote consensus, production PKI, and distributed replication.

## What is implemented

The strict path implements:

1. Candidate Act construction with explicit load-bearing fields.
2. Deterministic canonicalization (`REFCANON-1`) and SHA-256 act digest.
3. Execution Handle issuance with sink binding, expiry, generation vector, reuse policy, optional workload key binding, and integrity MAC.
4. Sink-local reconstruction of the live Candidate Act.
5. Handle integrity, expiry, sink, generation, revocation, act-digest, key-binding, and reuse checks.
6. A SQLite `BEGIN IMMEDIATE` transaction that serializes **verify → consume → protected local commit**.
7. `SINGLE_USE`, `COUNTED`, and an explicitly marked experimental `ENVELOPE` profile.
8. Finality Receipt generation.
9. Fail-closed behavior when consume state is unavailable.
10. Tests that prove adjacent credentials or receipts are not silently accepted as finality authority.

## Repository map

```text
execution_handle_ref/
  canonical.py      deterministic reference canonicalization
  cad.py            Candidate Act creation and act digest
  crypto.py         HMAC integrity + optional workload PoP for the zero-dependency profile
  engine.py         issue, reconstruct, verify, consume, commit, receipt
  errors.py         illustrative EF failure codes
  models.py         CAD / ExecutionHandle / FinalityReceipt models
  store.py          SQLite crash-safe consume/effect store

tests/
  test_reference.py 36 adversarial and positive tests

test_vectors/
  canonicalization_vectors.json

interop/
  python_digest.py
  node_digest.mjs
  go_digest.go

scripts/
  run_all.py          tests + cross-language digest comparison
  profile_matrix.py   domain/concurrency variable matrix
  benchmark.py        local reference benchmark
  mutation_probe.py   deterministic mutation/canonicalization property probe
  demo.py             minimal first-run example

docs/
  THREAT_MODEL.md
  CONFORMANCE.md
  SPEC_MAPPING.md
  LIMITATIONS.md
  FAQ.md
  CRITIC_REVIEW.md

results/
  latest.json
  profile-matrix.json
  benchmark.json
```

## Quick start

Requirements for the core implementation: **Python 3.11+ only**. No third-party Python package is required.

```bash
python -m unittest discover -s tests -v
python scripts/run_all.py
python scripts/profile_matrix.py
python scripts/benchmark.py
python scripts/mutation_probe.py
```

Optional interop checks use Node.js and Go if installed:

```bash
python interop/python_digest.py
node interop/node_digest.mjs
go run interop/go_digest.go
```

## Minimal example

```python
from execution_handle_ref import make_cad, ReferenceEngine, SQLiteStore, EFError

NOW = 2_000_000_000
store = SQLiteStore("finality.db")
engine = ReferenceEngine(store, sink_id="payment-post", clock=lambda: NOW)

cad = make_cad(
    act_type="PAYMENT_POST",
    consequence_class="financial",
    actor="agent-7",
    operation="post_payment",
    arguments={"amount_minor": 12500, "currency": "INR"},
    destination="acct:beneficiary-A",
    finality_sink="payment-post",
    policy_generation=1,
    purpose="invoice_settlement",
    now=NOW,
)

handle = engine.issue(cad, reuse_policy="SINGLE_USE")
receipt = engine.consume_and_commit(cad, handle)
print(receipt.decision)  # EFFECTUATED

try:
    engine.consume_and_commit(cad, handle)
except EFError as e:
    print(e.code)        # EF-005
```

## Core invariant

For a live act `C'`, handle `H`, sink `S'`, current generations `g_now`, and protected consume state `Store`:

```text
Auth(H, C', S', g_now, Store, t)
    iff Integrity(H)
    and t < H.expires_at
    and Sink(H) = S'
    and Digest(Reconstruct(C')) = H.act_digest
    and Current(H.generations, g_now)
    and OptionalBindingOK(H, C')
    and ReuseOK(H, Store, C')
```

For the strict reference profile, protected effectuation is permitted only inside the serialized boundary:

```text
atomic {
    reconstruct live effect
    re-check integrity/currentness/revocation/sink/exact-act binding
    consume SINGLE_USE / COUNTED state
    commit protected effect
}
```

An earlier successful verification is only a hint. The implementation deliberately includes a test in which early verification succeeds, revocation lands, and the in-transaction verification rejects the commit with `EF-062`.

## Why sink reconstruction matters

The caller does **not** get to make a changed operation look authorized by forwarding an old digest. `ReferenceEngine.reconstruct()` recomputes `arguments_digest` from the live fields presented to the sink immediately before effectuation. The test suite mutates payment amount while retaining the caller's stale digest; the sink recomputation turns that into `EF-023`.

This reference cannot magically observe a real payment rail or actuator. In the harness, the `CandidateAct` supplied to `consume_and_commit()` represents the fields observed by the sink adapter. A real adapter must construct that object from the actual pending operation, not from an untrusted duplicate supplied by the requester.

## Reuse policies

### SINGLE_USE

Exactly one protected commit can win. A second presentation returns `EF-005`. A 64-worker race is included in `profile_matrix.py`.

### COUNTED

A protected counter is incremented in the same transaction as commit and rejects when `max_uses` would be exceeded. The base draft's exact-act digest means all counted uses remain the same authorized act unless a profile defines additional semantics.

### ENVELOPE — important implementation finding

The draft says `ENVELOPE` can authorize non-identical repeated acts inside bounds, while the formal `Auth` predicate requires `d(C') = H.d`. Non-identical acts normally have non-identical digests. The reference therefore **does not silently invent base-protocol semantics**.

Two behaviors are provided:

- A base `ENVELOPE` handle created with `issue(..., reuse_policy="ENVELOPE")` is rejected at effectuation with `EF-042` because the binding rule is underspecified.
- `issue_envelope()` enables **experimental profile `EH-REF-ENVELOPE-1`**. It binds a digest over invariant fields plus the textual envelope constraints, while keeping the full live act digest in protected replay state. Only explicitly named paths may vary. Identical replay remains forbidden unless `allow_identical_replay=true`.

This profile is deliberately labeled experimental so reviewers can challenge or replace it without confusing it with the base draft.

## Deterministic canonicalization

The implementation defines a narrow profile, `REFCANON-1`:

- UTF-8;
- recursively sorted object keys;
- no insignificant whitespace;
- strings, booleans, null, arrays, objects, and signed integers;
- floats are forbidden;
- Python core accepts signed 64-bit integers;
- the shared Python/Node/Go interop vectors stay within JavaScript's exact integer range.

This is not represented as full RFC 8785 JCS. It is an explicitly declared deterministic profile used to make the test harness dependency-free and cross-language behavior reviewable. A production JSON profile can replace it with JCS; a CBOR profile can use deterministic CBOR.

## Cryptography in this repository

The zero-dependency implementation uses HMAC-SHA-256 for:

- issuer integrity over the Execution Handle;
- sink integrity over the Finality Receipt;
- optional workload proof-of-possession in the test profile.

This is a test profile, not a recommendation that unrelated organizations share HMAC keys. Public-key signatures, COSE, CWT, HSM-backed keys, workload identity binding, rotation, and trust-anchor distribution are deployment/profile concerns not implemented here.

## Test variables

The harness varies more than input strings:

| Variable | Values exercised |
|---|---|
| Domain profile | agent tool, payment, cloud/data egress, industrial actuation |
| Mutation | arguments, destination, stale digest, integrity, sink |
| Time | valid, expired, revocation after early verify |
| Reuse | SINGLE_USE, COUNTED, experimental ENVELOPE |
| Concurrency | 2, 8, 32, 64 simultaneous workers |
| Store state | available, unavailable/fail-closed |
| Identity | no PoP, missing PoP, valid PoP + wrong act, valid PoP + correct act |
| Canonical data | reordered keys, Unicode, arrays, signed integers, forbidden floats |
| Authority object | handle, finality receipt, attestation-shaped object, SCITT-shaped receipt, arbitrary token string |
| Path coverage | mediated path and an intentionally simulated bypass path |
| Crash | after consume/before local commit |

## Failure cases covered

The tests exercise these draft-local codes:

- `EF-002 NO_FINALITY_AUTHORITY`
- `EF-003 HANDLE_INTEGRITY_FAILURE`
- `EF-004 HANDLE_EXPIRED`
- `EF-005 AUTHORITY_ALREADY_USED`
- `EF-006 REPLAY_DETECTED`
- `EF-012 SCOPE_MISMATCH`
- `EF-020 DESTINATION_MISMATCH`
- `EF-023 ACT_DIGEST_MISMATCH`
- `EF-040 SINK_MISMATCH`
- `EF-041 GENERATION_STALE`
- `EF-042 REUSE_POLICY_VIOLATION`
- `EF-043 ENVELOPE_EXCEEDED`
- `EF-062 REVOCATION_ACTIVE`
- `EF-081 CONSUME_STATE_UNAVAILABLE`

Not every defined draft error is forced merely to raise test-count numbers. `EF-070` and `EF-080`, for example, need profile-specific escalation/degraded-mode semantics not necessary for the strict baseline harness.

## What a passing test suite proves — and does not prove

A passing suite provides executable evidence that **this implementation** enforces its stated invariant under the modeled conditions. It demonstrates concrete rejection behavior for substitution, replay, wrong sink, stale generation, revocation races, wrong authority object, consume-state loss, and concurrency.

It does **not** prove:

- that the PED/issuer made a correct policy decision;
- that every security-relevant field in a real deployment was included in the CAD;
- that a real sink reconstructed those fields correctly;
- that every alternate path to the consequence is mediated;
- that HMAC key management is production-grade;
- that remote external side effects are atomically coupled to SQLite;
- that the protocol has no undiscovered design flaw;
- that this design is standardized, adopted, or endorsed by any vendor or standards body.

See `docs/LIMITATIONS.md` and `docs/CRITIC_REVIEW.md` before citing results.

## Reproducing the recorded result

```bash
python scripts/run_all.py
python scripts/profile_matrix.py
python scripts/benchmark.py
cat results/latest.json
cat results/profile-matrix.json
cat results/benchmark.json
```

`results/latest.json` records the actual platform and raw outputs. Do not replace it with manually edited benchmark text when publishing results.

## Cross-system CI

`.github/workflows/conformance.yml` runs the Python suite across Ubuntu, Windows, and macOS with multiple Python versions, and runs Python/Node/Go canonicalization interop on Ubuntu. A green CI matrix is stronger cross-platform evidence than claiming those systems from a single local run.

The checked-in `results/` only claims the environment actually executed here. Windows and macOS should be described as **configured for CI**, not locally verified, until GitHub Actions runs them.

## Suggested reviewer workflow

1. Run the existing suite unchanged.
2. Read `docs/THREAT_MODEL.md` and identify an assumption the implementation hides.
3. Add a failing test before changing the code.
4. Try to produce two effects from one `SINGLE_USE` handle.
5. Try to mutate a load-bearing field without changing the sink-reconstructed digest.
6. Try to land revocation after an early check but before protected commit.
7. Try to make a Finality Receipt, OAuth-like token, workload credential, or attestation-shaped object authorize the effect by itself.
8. Add an alternate path to the effect and show why path coverage is a deployment property, not a token property.
9. Challenge `EH-REF-ENVELOPE-1`; it is explicitly experimental.
10. Report the smallest counterexample. A reproducible counterexample is more useful than a general claim either for or against the architecture.

## Criticism and prior art

Corrections, prior art, negative results, alternative constructions, and tests that falsify an invariant are welcome. If an existing protocol or product already requires sink-local reconstruction of the exact live act, sink binding, currentness, atomic/bounded consumption, and complete consequence-path mediation, document the precise mechanism and add a comparative test rather than relying on labels alone.

## License / IPR notice

See `LICENSE-NOTICE.md`. The repository deliberately separates the ability to inspect and reproduce the reference tests from any implication of a patent license or production-use grant.
