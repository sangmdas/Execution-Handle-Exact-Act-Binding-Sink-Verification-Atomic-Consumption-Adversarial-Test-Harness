# Security Policy for the Reference Repository

Please report reproducible security or invariant failures with the smallest test case possible. Particularly useful reports involve replay races, canonicalization disagreement, wrong-sink acceptance, revocation timing, crash/recovery duplication, or alternate consequence paths.

Do not treat repository secrets as real secrets: default HMAC keys are development constants and intentionally unsuitable for production.
