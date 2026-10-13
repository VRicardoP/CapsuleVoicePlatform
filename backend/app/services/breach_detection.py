"""
Automatic breach detection service.

Periodically scans the audit_log table for anomalous patterns and
creates SecurityBreach entries via SecurityBreachRepository.

RGPD Art. 33: Breach notification within 72 hours
NIS2 Art. 23: Incident reporting

Detected patterns:
1. Brute force: >10 login failures from same IP in 5 minutes
2. Anomalous access: >50 failed requests from same IP in 10 minutes
3. Data exfiltration: >20 data export actions by same user in 1 hour

security_breaches PRODUCTION schema:
  id, detected_at, detected_by, detection_method, breach_type, severity,
  nature, categories_affected, approximate_records, risk_level,
  authority_notification_deadline, status, ...
NOTE: Production columns differ from ORM model. Queries use production names.
"""

import hashlib
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.gdpr_repository import SecurityBreachRepository

logger = logging.getLogger(__name__)

# Detection thresholds
BRUTE_FORCE_THRESHOLD = 10
BRUTE_FORCE_WINDOW_MINUTES = 5

ANOMALOUS_ACCESS_THRESHOLD = 50
ANOMALOUS_ACCESS_WINDOW_MINUTES = 10

EXFILTRATION_THRESHOLD = 20
EXFILTRATION_WINDOW_MINUTES = 60

# Don't re-alert for the same pattern within this window
DEDUP_WINDOW_HOURS = 24

# Counter for generating unique breach references within a cycle
_cycle_counter = 0


class BreachDetectionService:
    """Scans audit_log for security anomalies and registers breaches."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]):
        self.session_maker = session_maker

    async def run_detection_cycle(self) -> list[dict]:
        """Execute all detection rules. Returns list of detected breaches."""
        async with self.session_maker() as session:
            breaches: list[dict] = []

            breaches.extend(await self._detect_brute_force(session))
            breaches.extend(await self._detect_anomalous_access(session))
            breaches.extend(await self._detect_data_exfiltration(session))

            if breaches:
                repo = SecurityBreachRepository(session)
                for breach_data in breaches:
                    fingerprint = breach_data.pop("_fingerprint", "")
                    if not await self._is_duplicate(session, fingerprint):
                        await repo.register_breach(**breach_data)
                    else:
                        logger.debug(
                            "Skipping duplicate breach fingerprint=%s",
                            fingerprint,
                        )
                await session.commit()

            return breaches

    async def _detect_brute_force(self, session: AsyncSession) -> list[dict]:
        """Detect brute force login attempts.

        Looks for >THRESHOLD login_failed actions from same IP
        in the last WINDOW minutes.
        """
        window_start = datetime.now(UTC) - timedelta(minutes=BRUTE_FORCE_WINDOW_MINUTES)

        result = await session.execute(
            text("""
                SELECT ip_address::text, COUNT(*) as attempt_count
                FROM audit_log
                WHERE action = 'FAILED_LOGIN'
                  AND created_at >= :window_start
                  AND ip_address IS NOT NULL
                GROUP BY ip_address
                HAVING COUNT(*) > :threshold
            """),
            {
                "window_start": window_start,
                "threshold": BRUTE_FORCE_THRESHOLD,
            },
        )

        breaches = []
        for row in result.fetchall():
            ip = row[0]
            count = row[1]
            fingerprint = _make_fingerprint("brute_force", ip)
            description = (
                f"Brute force detected: {count} failed login attempts "
                f"from IP {ip} in {BRUTE_FORCE_WINDOW_MINUTES} minutes"
            )
            breaches.append(
                {
                    "breach_type": "confidentiality",
                    "severity": "high",
                    "nature": description,
                    "risk_level": "possible",
                    "approximate_records": 0,
                    "categories_affected": [],
                    "detection_method": "brute_force_pattern",
                    "_fingerprint": fingerprint,
                }
            )

        return breaches

    async def _detect_anomalous_access(self, session: AsyncSession) -> list[dict]:
        """Detect anomalous access patterns.

        Looks for >THRESHOLD failed access attempts from same IP.
        """
        window_start = datetime.now(UTC) - timedelta(
            minutes=ANOMALOUS_ACCESS_WINDOW_MINUTES
        )

        result = await session.execute(
            text("""
                SELECT ip_address::text, COUNT(*) as fail_count
                FROM audit_log
                WHERE created_at >= :window_start
                  AND ip_address IS NOT NULL
                  AND action IN ('FAILED_LOGIN', 'RATE_LIMIT_EXCEEDED')
                GROUP BY ip_address
                HAVING COUNT(*) > :threshold
            """),
            {
                "window_start": window_start,
                "threshold": ANOMALOUS_ACCESS_THRESHOLD,
            },
        )

        breaches = []
        for row in result.fetchall():
            ip = row[0]
            count = row[1]
            fingerprint = _make_fingerprint("anomalous_access", ip)
            description = (
                f"Anomalous access pattern: {count} failed requests "
                f"from IP {ip} in {ANOMALOUS_ACCESS_WINDOW_MINUTES} minutes"
            )
            breaches.append(
                {
                    "breach_type": "confidentiality",
                    "severity": "medium",
                    "nature": description,
                    "risk_level": "possible",
                    "approximate_records": 0,
                    "categories_affected": [],
                    "detection_method": "anomalous_access_pattern",
                    "_fingerprint": fingerprint,
                }
            )

        return breaches

    async def _detect_data_exfiltration(self, session: AsyncSession) -> list[dict]:
        """Detect potential data exfiltration.

        Looks for >THRESHOLD data_export actions by same user in the last hour.
        """
        window_start = datetime.now(UTC) - timedelta(minutes=EXFILTRATION_WINDOW_MINUTES)

        result = await session.execute(
            text("""
                SELECT user_id::text, COUNT(*) as export_count
                FROM audit_log
                WHERE action = 'DATA_EXPORT'
                  AND created_at >= :window_start
                  AND user_id IS NOT NULL
                GROUP BY user_id
                HAVING COUNT(*) > :threshold
            """),
            {
                "window_start": window_start,
                "threshold": EXFILTRATION_THRESHOLD,
            },
        )

        breaches = []
        for row in result.fetchall():
            user_id = row[0]
            count = row[1]
            fingerprint = _make_fingerprint("exfiltration", user_id)
            description = (
                f"Potential data exfiltration: {count} data export requests "
                f"by user {user_id} in {EXFILTRATION_WINDOW_MINUTES} minutes"
            )
            breaches.append(
                {
                    "breach_type": "confidentiality",
                    "severity": "critical",
                    "nature": description,
                    "risk_level": "likely",
                    "approximate_records": count,
                    "categories_affected": ["personal_data"],
                    "detection_method": "exfiltration_pattern",
                    "_fingerprint": fingerprint,
                }
            )

        return breaches

    async def _is_duplicate(self, session: AsyncSession, fingerprint: str) -> bool:
        """Check if a breach with the same fingerprint was already registered recently."""
        if not fingerprint:
            return False

        window_start = datetime.now(UTC) - timedelta(hours=DEDUP_WINDOW_HOURS)

        result = await session.execute(
            text("""
                SELECT EXISTS(
                    SELECT 1 FROM security_breaches
                    WHERE detected_at >= :window_start
                      AND nature LIKE :pattern
                )
            """),
            {
                "window_start": window_start,
                "pattern": f"%{fingerprint}%",
            },
        )
        return result.scalar() or False


def _make_fingerprint(pattern_type: str, identifier: str) -> str:
    """Create a dedup fingerprint for a detection pattern."""
    raw = f"{pattern_type}:{identifier}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
