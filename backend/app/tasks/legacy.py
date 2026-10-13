"""Legacy background tasks migrated from main.py asyncio loops to ARQ cron jobs.

These tasks were previously running as asyncio.create_task() loops in the
FastAPI lifespan. Now they run as ARQ cron jobs in the worker process.
"""

import logging
from datetime import UTC

from app.core.tasks import create_logged_task

logger = logging.getLogger(__name__)


async def recording_cleanup(ctx: dict) -> dict:
    """Cron: delete expired recordings (daily)."""
    from app.config.settings import settings
    from app.services.recording_service import RecordingService

    if not settings.recording_enabled:
        return {"skipped": True}

    rec_service = RecordingService(settings)
    deleted, freed = await rec_service.cleanup_expired()
    if deleted:
        logger.info(
            "Recording cleanup completed",
            extra={"deleted": deleted, "freed_mb": round(freed / 1024 / 1024, 1)},
        )
    return {"deleted": deleted, "freed_mb": round(freed / 1024 / 1024, 1)}


async def breach_detection(ctx: dict) -> int:
    """Cron: detect security breaches (every 5 min)."""
    from app.config.database import async_session_maker
    from app.services.breach_detection import BreachDetectionService

    detector = BreachDetectionService(async_session_maker)
    breaches = await detector.run_detection_cycle()
    if breaches:
        logger.warning("Breaches detected", extra={"count": len(breaches)})
    return len(breaches) if breaches else 0


async def whatsapp_campaign_scheduler(ctx: dict) -> int:
    """Cron: check for scheduled WhatsApp campaigns + A/B winner selection (every 30s)."""
    from datetime import datetime

    from sqlalchemy import select

    from app.config.database import async_session_maker
    from app.models.whatsapp import WACampaign
    from app.services.whatsapp_campaign_service import CampaignSendingService

    sender = CampaignSendingService(async_session_maker)
    count = 0

    async with async_session_maker() as db:
        now = datetime.now(UTC)

        # 1. Start scheduled campaigns
        result = await db.execute(
            select(WACampaign).where(
                WACampaign.status == "scheduled",
                WACampaign.scheduled_at <= now,
            )
        )
        campaigns = result.scalars().all()
        for c in campaigns:
            c.status = "sending"
            c.started_at = now
            await db.commit()
            create_logged_task(sender.start_campaign(c.id), name=f"wa-scheduled-{c.id}")
            logger.info("Auto-started scheduled campaign", extra={"campaign_id": str(c.id)})
            count += 1

        # 2. A/B test auto-winner selection
        ab_result = await db.execute(
            select(WACampaign).where(
                WACampaign.is_ab_test == True,
                WACampaign.ab_parent_id.is_(None),
                WACampaign.ab_auto_select == True,
                WACampaign.ab_winner_variant_id.is_(None),
                WACampaign.status == "completed",
            )
        )
        ab_parents = ab_result.scalars().all()
        for parent in ab_parents:
            if not parent.completed_at:
                continue
            hours_since = (now - parent.completed_at).total_seconds() / 3600
            if hours_since < parent.ab_auto_select_hours:
                continue

            variants_result = await db.execute(
                select(WACampaign).where(
                    WACampaign.ab_parent_id == parent.id,
                    WACampaign.status == "completed",
                )
            )
            variants = variants_result.scalars().all()
            if not variants:
                continue

            def _metric(c):
                total = c.total_recipients or 1
                if parent.ab_winner_metric == "read_rate":
                    return c.read_count / total
                elif parent.ab_winner_metric == "delivered_rate":
                    return c.delivered_count / total
                return c.read_count / total

            winner = max(variants, key=_metric)
            parent.ab_winner_variant_id = winner.id
            await db.commit()
            logger.info(
                "A/B auto-winner selected",
                extra={"parent_id": str(parent.id), "winner_id": str(winner.id)},
            )

    return count


async def sla_check(ctx: dict) -> dict:
    """Cron: check WhatsApp SLA breaches (every 60s)."""
    from app.config.database import async_session_maker
    from app.services.whatsapp_sla_service import SlaCheckService

    sla_checker = SlaCheckService(async_session_maker)
    breaches = await sla_checker.run_check_cycle()
    escalated = await sla_checker.escalate_breaches()
    if breaches:
        logger.warning("SLA breaches detected", extra={"count": breaches})
    if escalated:
        logger.warning("SLA breaches escalated", extra={"count": escalated})
    return {"breaches": breaches or 0, "escalated": escalated or 0}


async def cleanup_expired_sessions(ctx: dict) -> dict:
    """Cron: mark expired sessions/tokens as revoked and purge old revoked rows (every 6h)."""
    from sqlalchemy import text

    from app.config.database import async_session_maker

    async with async_session_maker() as db:
        # Mark expired-but-not-yet-revoked sessions as revoked
        r1 = await db.execute(
            text("""
            UPDATE frontend_sessions
            SET is_revoked = TRUE, revoked_reason = 'expired_cleanup', revoked_at = NOW()
            WHERE NOT is_revoked
              AND (idle_expires_at < NOW() OR absolute_expires_at < NOW())
        """)
        )
        # Hard-delete rows revoked more than 7 days ago
        r2 = await db.execute(
            text("""
            DELETE FROM frontend_sessions
            WHERE is_revoked = TRUE
              AND COALESCE(revoked_at, idle_expires_at) < NOW() - INTERVAL '7 days'
        """)
        )
        # Mark expired API tokens as revoked
        r3 = await db.execute(
            text("""
            UPDATE api_tokens SET is_revoked = TRUE, revoked_reason = 'expired'
            WHERE NOT is_revoked AND expires_at < NOW()
        """)
        )
        await db.commit()

    result = {
        "sessions_marked": r1.rowcount,
        "sessions_purged": r2.rowcount,
        "tokens_revoked": r3.rowcount,
    }
    if any(result.values()):
        logger.info("Session cleanup completed", extra=result)
    return result
