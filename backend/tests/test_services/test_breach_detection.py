"""Tests for BreachDetectionService.

Uses the real DB (via db_session fixture) to test detection queries
against the audit_log table.

audit_log real columns: id, user_id (FK→users), action (CHECK), entity_type (NOT NULL),
                        ip_address, created_at, severity, details, ...
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.services.breach_detection import (
    BRUTE_FORCE_THRESHOLD,
    EXFILTRATION_THRESHOLD,
    BreachDetectionService,
    _make_fingerprint,
)

# ─── Helper ────────────────────────────────────────────────────────────────


async def _insert_audit_entry(
    session,
    action: str,
    ip_address: str | None = "10.0.0.1",
    user_id: str | None = None,
    timestamp: datetime | None = None,
):
    """Insert a row into audit_log for testing.

    user_id has FK to users — pass a valid user ID from conftest or None.
    """
    ts = timestamp or datetime.now(UTC)
    await session.execute(
        text("""
            INSERT INTO audit_log (
                action, entity_type, ip_address, created_at, user_id
            ) VALUES (
                :action, 'auth', :ip_address, :created_at,
                CAST(:user_id AS UUID)
            )
        """),
        {
            "action": action,
            "ip_address": ip_address,
            "created_at": ts,
            "user_id": user_id,
        },
    )


async def _get_test_user_id(session) -> str:
    """Get the ID of the test user created by conftest."""
    result = await session.execute(text("SELECT current_setting('app.current_user_id', true)"))
    return result.scalar()


# ─── Tests ────────────────────────────────────────────────────────────────


async def test_no_breaches_on_empty_audit_log(db_session):
    """No breaches when audit_log has no suspicious activity."""
    # Test individual detection methods directly (no commit attempt)
    service = BreachDetectionService.__new__(BreachDetectionService)
    brute = await service._detect_brute_force(db_session)
    anomalous = await service._detect_anomalous_access(db_session)
    exfiltration = await service._detect_data_exfiltration(db_session)
    assert brute == []
    assert anomalous == []
    assert exfiltration == []


async def test_detect_brute_force_above_threshold(db_session):
    """Detects brute force when login failures exceed threshold."""
    attacker_ip = "192.168.1.100"

    # Insert enough login failures (no user_id needed for brute force)
    for _ in range(BRUTE_FORCE_THRESHOLD + 5):
        await _insert_audit_entry(
            db_session,
            action="FAILED_LOGIN",
            ip_address=attacker_ip,
        )

    service = BreachDetectionService.__new__(BreachDetectionService)
    breaches = await service._detect_brute_force(db_session)

    assert len(breaches) == 1
    assert breaches[0]["severity"] == "high"
    assert breaches[0]["detection_method"] == "brute_force_pattern"
    assert attacker_ip in breaches[0]["nature"]
    assert str(BRUTE_FORCE_THRESHOLD + 5) in breaches[0]["nature"]


async def test_no_brute_force_below_threshold(db_session):
    """No brute force breach when login failures are below threshold."""
    for _ in range(BRUTE_FORCE_THRESHOLD - 1):
        await _insert_audit_entry(
            db_session,
            action="FAILED_LOGIN",
            ip_address="10.0.0.50",
        )

    service = BreachDetectionService.__new__(BreachDetectionService)
    breaches = await service._detect_brute_force(db_session)

    # Filter to only this IP (other tests may leave data)
    relevant = [b for b in breaches if "10.0.0.50" in b.get("nature", "")]
    assert len(relevant) == 0


async def test_detect_data_exfiltration(db_session):
    """Detects data exfiltration when exports exceed threshold."""
    # Use the test user created by conftest (has valid FK)
    test_user_id = await _get_test_user_id(db_session)

    for _ in range(EXFILTRATION_THRESHOLD + 5):
        await _insert_audit_entry(
            db_session,
            action="DATA_EXPORT",
            user_id=test_user_id,
        )

    service = BreachDetectionService.__new__(BreachDetectionService)
    breaches = await service._detect_data_exfiltration(db_session)

    assert len(breaches) == 1
    assert breaches[0]["severity"] == "critical"
    assert breaches[0]["detection_method"] == "exfiltration_pattern"
    assert test_user_id in breaches[0]["nature"]


async def test_make_fingerprint_deterministic():
    """Fingerprints are deterministic for same inputs."""
    fp1 = _make_fingerprint("brute_force", "192.168.1.1")
    fp2 = _make_fingerprint("brute_force", "192.168.1.1")
    fp3 = _make_fingerprint("brute_force", "192.168.1.2")
    assert fp1 == fp2
    assert fp1 != fp3


async def test_old_events_not_detected(db_session):
    """Events outside the detection window are not flagged."""
    old_timestamp = datetime.now(UTC) - timedelta(hours=2)

    for _ in range(BRUTE_FORCE_THRESHOLD + 5):
        await _insert_audit_entry(
            db_session,
            action="FAILED_LOGIN",
            ip_address="10.0.0.99",
            timestamp=old_timestamp,
        )

    service = BreachDetectionService.__new__(BreachDetectionService)
    breaches = await service._detect_brute_force(db_session)

    # Old events from this IP should not be detected
    relevant = [b for b in breaches if "10.0.0.99" in b.get("nature", "")]
    assert len(relevant) == 0


async def test_multiple_ips_detected_separately(db_session):
    """Different IPs that exceed threshold are reported independently."""
    for ip in ["10.1.1.1", "10.2.2.2"]:
        for _ in range(BRUTE_FORCE_THRESHOLD + 1):
            await _insert_audit_entry(
                db_session,
                action="FAILED_LOGIN",
                ip_address=ip,
            )

    service = BreachDetectionService.__new__(BreachDetectionService)
    breaches = await service._detect_brute_force(db_session)

    ips_detected = {b["nature"] for b in breaches}
    assert any("10.1.1.1" in n for n in ips_detected)
    assert any("10.2.2.2" in n for n in ips_detected)
