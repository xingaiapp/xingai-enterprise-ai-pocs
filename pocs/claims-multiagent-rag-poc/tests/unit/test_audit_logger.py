"""Audit logger tests."""

from claims_rag.audit.audit_logger import AuditLogger, redact


def test_redact_ssn_pattern() -> None:
    text = "Claimant SSN 123-45-6789 filed."
    assert "[REDACTED]" in redact(text)
    assert "123-45-6789" not in redact(text)


def test_audit_logger_append_only(audit_db_path) -> None:
    logger = AuditLogger(db_path=audit_db_path)
    logger.log_step("trace-1", agent="intake", input_data={"raw": "test"}, output_data={"ok": True})
    logger.log_step("trace-1", agent="retrieval", input_data={"q": "policy"}, output_data={"n": 2})
    rows = logger.get_trace("trace-1")
    assert len(rows) == 2
    assert rows[0]["agent"] == "intake"
    assert rows[1]["agent"] == "retrieval"
