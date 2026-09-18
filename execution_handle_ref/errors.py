from __future__ import annotations

class EFError(Exception):
    """Protocol-visible rejection carrying an illustrative EF code."""
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message

EF002 = "EF-002"  # NO_FINALITY_AUTHORITY
EF003 = "EF-003"  # HANDLE_INTEGRITY_FAILURE
EF004 = "EF-004"  # HANDLE_EXPIRED
EF005 = "EF-005"  # AUTHORITY_ALREADY_USED
EF006 = "EF-006"  # REPLAY_DETECTED
EF012 = "EF-012"  # SCOPE_MISMATCH
EF020 = "EF-020"  # DESTINATION_MISMATCH
EF023 = "EF-023"  # ACT_DIGEST_MISMATCH
EF040 = "EF-040"  # SINK_MISMATCH
EF041 = "EF-041"  # GENERATION_STALE
EF042 = "EF-042"  # REUSE_POLICY_VIOLATION
EF043 = "EF-043"  # ENVELOPE_EXCEEDED
EF062 = "EF-062"  # REVOCATION_ACTIVE
EF070 = "EF-070"  # ESCALATION_REQUIRED
EF080 = "EF-080"  # FAIL_CLOSED
EF081 = "EF-081"  # CONSUME_STATE_UNAVAILABLE
