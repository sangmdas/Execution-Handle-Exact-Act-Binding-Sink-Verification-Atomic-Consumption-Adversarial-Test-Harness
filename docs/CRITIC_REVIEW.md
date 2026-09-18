# Adversarial Review / Falsification Guide

This repository is intentionally structured so disagreement can be converted into tests.

## High-value counterexamples

A reviewer can materially challenge the design by demonstrating any of the following under the claimed strict assumptions:

1. **Double effect:** two successful protected commits from one `SINGLE_USE` handle.
2. **Substitution:** a live load-bearing field changes but the sink still accepts the old handle without a hash collision.
3. **Wrong sink:** a handle for sink A commits at sink B.
4. **Revocation race:** revocation becomes current before protected commit, yet commit succeeds.
5. **Store ambiguity:** consume-state loss is interpreted as unused and effectuation proceeds in strict mode.
6. **Receipt confusion:** a receipt/evidence object is accepted as effectuation authority.
7. **Canonicalization split:** two conforming implementations produce different bytes/digests for an allowed value.
8. **Crash duplicate:** an allowed crash/recovery sequence produces two irreversible effects.
9. **Envelope inconsistency:** a supposedly bounded variation escapes constraints or the base semantics cannot be coherently specified.
10. **Prior-art equivalence:** an existing standardized construction already imposes all relevant invariants, making a separate mechanism redundant.

## How to submit a useful criticism

Prefer:

```text
Assumption challenged:
Minimal input/state:
Interleaving or mutation:
Observed result:
Expected invariant:
Why existing test coverage misses it:
Proposed new test:
```

A failing executable test is preferred over a general statement that the architecture is either “obvious” or “impossible.”

## Claims that should be rejected if made about this repository

The repository does not establish that:

- every OAuth/RAR/DPoP system has a finality gap;
- every transaction system lacks exact-act binding;
- every vendor architecture is bypassable;
- the draft is standardized or adopted;
- the reference is production ready;
- the measured benchmark predicts hardware/silicon latency;
- one local database solves atomicity with remote effects;
- successful enforcement proves a policy was correct.

## Specification issue discovered by implementation

`ENVELOPE` currently needs a precise relationship among:

- `H.act_digest`;
- invariant/template fields;
- fields allowed to vary;
- the per-use live act digest;
- replay tracking;
- `candidate_act_id` / freshness semantics.

`EH-REF-ENVELOPE-1` is a candidate construction, not a resolution by declaration. Reviewers are invited to replace it with a cleaner model and corresponding vectors.
