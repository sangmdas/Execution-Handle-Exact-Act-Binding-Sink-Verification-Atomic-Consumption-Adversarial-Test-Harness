# Limitations and Non-Claims

Read this before using benchmark or test results in a paper, Internet-Draft, issue, presentation, or outreach message.

## 1. Local atomicity is not remote-effect atomicity

The reference effect is a SQLite row in the **same transaction** as consume state. That makes the local invariant genuinely testable. It does not make an external bank transfer, actuator movement, GPU DMA release, packet emission, or third-party API call atomic with SQLite.

A real sink needs a rail-native transaction, reservation/commit protocol, transactional outbox/inbox, idempotent effect key, hardware transaction, or equivalent construction. If the external effect can happen and the consume transaction can independently roll back, the reference proof no longer transfers automatically.

## 2. Sink reconstruction is represented, not magically obtained

`consume_and_commit(observed, handle)` treats `observed` as the sink's live view. The security property is only as good as the adapter that creates that view. If the adapter omits a load-bearing field or reads a stale shadow copy, a digest match can be meaningless.

## 3. CAD completeness is deployment-specific

The repository provides a representative field set. It cannot know every field that changes a real consequence. Defaults, tenant context, routing metadata, hidden headers, region choice, device channel, unit conversion, beneficiary alias resolution, or policy-derived values may also need to be bound.

## 4. Alternate paths defeat prevention claims

An admin console, debug API, legacy credential, replica endpoint, root shell, direct device bus, or alternate egress path can bypass the reference engine. The harness explicitly demonstrates this. A deployment must enumerate and mediate every path capable of producing the protected consequence.

## 5. HMAC is a convenience profile

HMAC-SHA-256 keeps the repository dependency-free. It does not solve multi-organization trust, public verification, HSM custody, key rotation, certificate lifecycle, issuer discovery, or algorithm agility.

## 6. `REFCANON-1` is not complete JCS

Floats are forbidden, Unicode normalization is not added beyond the input strings, and signed-integer limits are explicit. Production protocol profiles should use a standards-defined canonicalization and test edge cases across implementations.

## 7. ENVELOPE semantics are experimentally completed

`EH-REF-ENVELOPE-1` is one possible resolution to an ambiguity in the draft. It should not be described as normative. A better design may use a template digest, a policy object digest, Merkle commitments, parameter constraints, or a separate envelope authority object.

## 8. COUNTED needs domain semantics

Allowing the same exact act more than once is meaningful only if the domain defines what multiple uses mean. The reference tests the protected counter. It does not claim that repeated financial or physical effects are appropriate.

## 9. No hostile host protection

A user with sufficient local privileges can modify Python, SQLite, or keys. TEE/HSM/secure-element enforcement is outside this repository.

## 10. No distributed-consensus implementation

SQLite serializes one database. Multi-region replicas, quorum stores, leader changes, clock uncertainty, split brain, and disaster recovery are not modeled. A distributed implementation must preserve per-handle linearizability or a stronger domain-equivalent invariant.

## 11. Time model is simple

Tests use an injected integer clock. Clock rollback, leap seconds, synchronization failure, and secure time sources are not modeled.

## 12. Receipt persistence is local

Receipts are HMAC-protected and stored locally. SCITT publication, transparency logs, third-party receipt verification, privacy redaction, and long-term evidence retention are not implemented.

## 13. Privacy is only partially addressed

Act digests can leak information when underlying values have low entropy. The reference includes a freshness nonce in CAD construction, but it does not implement encrypted receipts, selective disclosure, or dedicated privacy-preserving commitments.

## 14. The benchmark is not comparative evidence

The benchmark reports this Python/SQLite implementation on one machine. It cannot establish superiority over OAuth gateways, payment systems, databases, hardware interlocks, or any vendor platform.

## 15. Passing tests do not prove absence of bugs

The suite provides reproducible evidence for known cases. It is not a formal proof, penetration test, certification, or exhaustive state-space exploration.
