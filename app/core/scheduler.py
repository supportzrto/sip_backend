import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config.settings import settings
from app.database.session import SessionLocal
from app.services.market_data_sync_service import MarketDataSyncService

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _run_scheduled_sync() -> None:
    """
    Entry point invoked by the scheduler. Runs in its own DB
    session, independent of any request.
    """

    session = SessionLocal()

    try:
        service = MarketDataSyncService(
            session=session,
            data_directory=settings.DATA_DIRECTORY,
        )

        service.sync()
        session.commit()

        logger.info("Scheduled market data sync completed.")

    except Exception:
        session.rollback()
        logger.exception("Scheduled market data sync failed.")

    finally:
        session.close()


def _run_scheduled_alerts() -> None:
    """
    Entry point invoked by the scheduler, shortly after the daily
    sync. Runs in its own DB session, independent of any request.

    Imports are deferred to inside the function (rather than at
    module level, alongside _run_scheduled_sync's imports) purely to
    keep this module's import-time footprint limited to what the
    sync job needs when alerts aren't relevant -- both jobs are only
    ever actually called from inside the scheduler either way.
    """

    from app.api.dependencies.alerts import get_alert_service

    session = SessionLocal()

    try:
        # get_alert_service is a FastAPI dependency (expects a
        # Session, not a request) -- calling it directly like this
        # outside of a request is the same pattern used by
        # MarketDataSyncService above.
        service = get_alert_service(db=session)

        service.run_all_active()

        logger.info("Scheduled alert evaluation completed.")

    except Exception:
        session.rollback()
        logger.exception("Scheduled alert evaluation failed.")

    finally:
        session.close()


def _compute_alert_trigger_time() -> tuple[int, int]:
    """
    The sync's hour/minute, offset forward by
    ALERT_SCHEDULE_DELAY_MINUTES, wrapping correctly across hour/day
    boundaries (e.g. a 18:50 sync with a 20-minute delay runs alerts
    at 19:10, not an invalid "18:70").
    """

    total_minutes = (
        settings.SYNC_SCHEDULE_HOUR * 60
        + settings.SYNC_SCHEDULE_MINUTE
        + settings.ALERT_SCHEDULE_DELAY_MINUTES
    ) % (24 * 60)

    return total_minutes // 60, total_minutes % 60


def start_scheduler() -> BackgroundScheduler | None:
    """
    Start the background scheduler if SYNC_SCHEDULE_ENABLED is set.

    Returns the scheduler instance (so it can be shut down on app
    shutdown), or None if scheduling is disabled.
    """

    global _scheduler

    if not settings.SYNC_SCHEDULE_ENABLED:
        return None

    _scheduler = BackgroundScheduler(
        timezone=settings.SYNC_SCHEDULE_TIMEZONE,
    )

    _scheduler.add_job(
        _run_scheduled_sync,
        trigger=CronTrigger(
            hour=settings.SYNC_SCHEDULE_HOUR,
            minute=settings.SYNC_SCHEDULE_MINUTE,
        ),
        id="daily_market_data_sync",
        replace_existing=True,
    )

    alert_hour, alert_minute = _compute_alert_trigger_time()

    _scheduler.add_job(
        _run_scheduled_alerts,
        trigger=CronTrigger(
            hour=alert_hour,
            minute=alert_minute,
        ),
        id="daily_alert_evaluation",
        replace_existing=True,
    )

    _scheduler.start()

    logger.info(
        "Scheduled daily market data sync at %02d:%02d %s, "
        "alert evaluation at %02d:%02d %s.",
        settings.SYNC_SCHEDULE_HOUR,
        settings.SYNC_SCHEDULE_MINUTE,
        settings.SYNC_SCHEDULE_TIMEZONE,
        alert_hour,
        alert_minute,
        settings.SYNC_SCHEDULE_TIMEZONE,
    )

    return _scheduler


def stop_scheduler() -> None:

    global _scheduler

    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None