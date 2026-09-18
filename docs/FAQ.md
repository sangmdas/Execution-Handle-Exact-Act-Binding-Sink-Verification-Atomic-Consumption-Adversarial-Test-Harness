# FAQ for Reviewers and Critics

## 1. Is this just another access token?

No in the strict profile. Possession alone is intentionally insufficient. The sink also reconstructs the live act, checks exact correspondence, sink identity, current generations/revocation, reuse state, and optional key binding before commit.

If a deployment skips those checks and accepts possession alone, it has degraded the object into ordinary bearer-style authority under this repository's terminology.

## 2. Is this just OAuth RAR with more fields?

RAR can carry detailed authorization information and may be part of a deployment. The testable question here is narrower: does the component making the consequence real reconstruct the current live operation and serialize that correspondence check with bounded/single-use consumption and protected commit? If an OAuth-based deployment already does all of that, it may satisfy the invariant under different names.

## 3. Doesn't DPoP or mTLS stop token theft?

Sender-constraining a credential answers who can present it. Exact-act binding answers what concrete effect may be produced at which sink and how many times. The repository includes a case where a valid workload proof exists for a mutated act; the act is still rejected.

## 4. Isn't HTTP Message Signatures enough?

A signed request can strongly bind a message. It does not by itself define sink-local reconstruction, current policy/revocation generation, single-use atomic consumption, or complete path mediation. A deployment may combine request signatures with this invariant.

## 5. Isn't this just an idempotency key?

Idempotency keys are close and often valuable prior art. A plain idempotency key commonly prevents duplicate processing of the same logical request. The strict handle additionally binds authority to the reconstructed act, sink, current generations, expiry, integrity, and optional identity proof. If an existing idempotency system already enforces those properties before effectuation, that is strong comparative evidence and should be tested directly.

## 6. Isn't a saga, 2PC, TCC, XA, or workflow engine enough?

Those mechanisms coordinate steps and recovery. They can be complementary. A coordinator still needs to know whether the child effect it is preparing/committing is the exact child act currently authorized. If every child step already reconstructs and consumes exact-act authority, the invariant is already present.

## 7. Why reconstruct at the sink? Why not trust the caller's digest?

Because the caller is the party that may have stale, substituted, or malicious inputs. A digest is useful only if the verifier knows it corresponds to the effect about to happen. Test 11 changes live amount while preserving the caller's old digest; the sink recomputes and rejects it.

## 8. What if the sink cannot observe all relevant fields?

Then it cannot claim exact-act prevention for fields it cannot observe or reliably bind. That is a profile/deployment limitation, not something hashing can repair.

## 9. What prevents a replay race on two replicas?

In the reference, a per-handle SQLite row is updated in a serialized transaction. The 2/8/32/64-worker tests allow only one `SINGLE_USE` commit. A distributed deployment needs per-handle linearizability or an equivalent reservation/commit construction.

## 10. Why must revocation be rechecked inside the atomic boundary?

Otherwise a handle can verify at `t1`, be revoked at `t2`, and still commit at `t3`. Test 10 deliberately creates that ordering and proves the in-boundary check rejects it.

## 11. What happens if the consume store is down?

The strict profile returns `EF-081` and does not effectuate. Availability is sacrificed to preserve the prevention invariant. A degraded mode can be designed, but it must not be described as equivalent to strict prevention.

## 12. What if the issuer is compromised or approves a bad act?

The mechanism can faithfully enforce a bad authorization. It does not determine policy correctness. Test 32 intentionally demonstrates this boundary.

## 13. Does a Finality Receipt authorize another effect?

No. Test 20 attempts to replay a receipt as authority and gets `EF-002`.

## 14. Can an attestation result or SCITT receipt replace a handle?

Not in this profile. Tests 21 and 22 reject them as authority objects. They can still provide evidence used by an issuer or policy system.

## 15. Why use HMAC rather than Ed25519/COSE?

To keep the reference zero-dependency and runnable on a stock Python installation. HMAC proves the integrity-path behavior in one trust domain. It is not a multi-party deployment recommendation.

## 16. Why invent `REFCANON-1`?

To make canonicalization explicit and cross-language testable without dependencies. The draft permits a declared deterministic canonicalization. Production profiles should strongly consider standards-defined JCS or deterministic CBOR.

## 17. Why forbid floats?

Cross-language floating-point formatting and numeric interpretation create avoidable digest ambiguity. Financial values can be represented as integer minor units; other domains can define scaled integers or a standards-defined number encoding.

## 18. Does Unicode key/value ordering work across languages?

The included Python, Node, and Go test vectors currently produce identical digests for the checked Unicode cases. That is evidence for those vectors, not a proof for every Unicode edge case.

## 19. Why is ENVELOPE special?

Because non-identical repeated acts cannot all equal one exact full-act digest. The base draft needs a clearer binding rule. This repository exposes that ambiguity and provides `EH-REF-ENVELOPE-1` only as an experimental candidate.

## 20. Why does base ENVELOPE return `EF-042` instead of guessing?

Silently inventing semantics would make the test suite look complete while actually testing a different protocol. An explicit rejection makes the specification question visible.

## 21. Doesn't COUNTED have a similar problem?

Potentially. If every counted use is literally the same exact act, a counter is coherent. If counted uses are expected to vary, the profile must define which fields are fixed and which may vary, just as ENVELOPE must.

## 22. What does the crash test prove?

With consume state and the reference effect in the same SQLite transaction, a simulated crash after consume but before commit rolls the transaction back; a later reverified attempt can succeed once. It does **not** prove atomicity with a remote irreversible effect.

## 23. What about a crash after a remote effect happened but before local consume was durable?

That is a serious integration problem. A real sink needs rail-native atomicity, reservation, idempotency, or a recoverable transaction/outbox protocol. The repository explicitly does not claim SQLite can solve this for an external system.

## 24. Can an alternate admin/debug path bypass the sink?

Yes. Test 31 demonstrates exactly that. Complete path mediation is an assumption that must be engineered and audited.

## 25. Does this prevent prompt injection or malicious model output?

Not by itself. It can prevent a changed or unauthorized concrete effect when that effect is mediated by the sink. It does not make model reasoning trustworthy and does not classify prompts.

## 26. Does this prevent data exfiltration?

Only for egress paths and data fields actually covered by the sink and CAD. Unmediated channels remain outside the guarantee.

## 27. Does it require a network round trip to the issuer on every effect?

Not in the reference. A handle carries issued state; current generations and reuse are checked locally at the sink. Production trust synchronization is a separate design problem.

## 28. Is the benchmark sub-millisecond?

The recorded local commit median is around 0.56 ms on one Linux x86_64 run. That number must not be generalized to networks, HSMs, replicated databases, remote rails, or hardware interlocks.

## 29. What systems were actually tested?

The checked result file records Linux x86_64 with Python 3.13.5. Node.js and Go were also executed there for digest interoperability. GitHub Actions is configured for Ubuntu, Windows, and macOS, but those systems should not be claimed as verified until CI actually runs.

## 30. How can a critic falsify the core claim?

Produce a reproducible case, under the stated assumptions, where a strict `SINGLE_USE` handle causes two protected commits; a mismatched live act commits; a revoked/stale handle commits after the in-boundary check; or an unrecognized authority object is accepted. Add the smallest failing test and explain which invariant it violates.

## 31. What result would narrow rather than falsify the claim?

Showing an unmodeled bypass, omitted load-bearing field, remote atomicity gap, compromised issuer, or distributed-store failure may show that a particular deployment cannot claim prevention. That is still valuable and should shrink the deployment claim.

## 32. What result would show the proposal is unnecessary?

A concrete existing mechanism that already mandates the same live-act reconstruction, sink binding, currentness, bounded consumption, protected commit, and consequence-path coverage would be strong evidence that a new object or protocol is unnecessary or should be reframed as a profile of that mechanism.
