# Threat Model

## Security question

Can an authentic, unexpired, otherwise valid authority object be used to cause an effect different from the act that was authorized, or be reused to cause an additional effect?

The harness focuses on correspondence and final effectuation, not on deciding which acts are ethically, legally, or operationally desirable.

## Adversary capabilities modeled

The test adversary can:

- possess a valid Execution Handle;
- mutate tool arguments after issuance;
- substitute a destination/beneficiary;
- present a handle at a different sink;
- replay an already consumed handle;
- race multiple workers against one single-use handle;
- retain a caller-supplied old digest while changing live arguments;
- wait until a handle expires;
- modify an integrity-protected handle without the issuer key;
- cause policy or revocation generations to change;
- land revocation after an early out-of-transaction verification;
- present a valid workload PoP for a different live act;
- present adjacent evidence objects instead of an Execution Handle;
- make consume state unavailable;
- attempt bounded/non-identical ENVELOPE uses;
- exploit an alternate unmediated path to the consequence.

## Trusted components in the reference profile

The strict prevention claim depends on:

1. issuer key integrity;
2. sink key integrity for receipt authenticity;
3. the correctness of the sink adapter's live-field reconstruction;
4. completeness of the load-bearing CAD field set;
5. collision resistance of SHA-256;
6. deterministic canonicalization;
7. integrity and monotonicity of SQLite consume state;
8. the atomic local transaction containing verification, consume, and local effect commit;
9. mediation of every viable path to the protected consequence.

Compromise of these assumptions shrinks the claim.

## Explicitly out of scope

- correctness of policy or legal interpretation;
- malicious or compromised issuer/PED authorizing a bad act;
- host/root compromise that can rewrite the reference process and database;
- side channels;
- cryptographic break of SHA-256/HMAC-SHA-256;
- remote external effects that do not participate in an atomic/reservation/outbox protocol;
- universal prevention of actions through bypass paths not mediated by an equivalent sink;
- proof that the draft is superior to every existing authorization/transaction mechanism.

## Consequence-path completeness

The test `test_31_alternate_raw_credential_path_demonstrates_path_coverage_limit` intentionally writes the reference effect table without an Execution Handle. It passes because it demonstrates a limitation: **if an alternate path can reach K without the sink, handle enforcement cannot prevent that path**.

That test must not be cited as “the bypass was prevented.” It demonstrates exactly the opposite and makes the bounded nature of the prevention claim visible.
