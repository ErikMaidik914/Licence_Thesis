import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
import signal
import asyncio

from .config import get_settings
from ..db.session import SessionLocal, engine
from ..services.gamification import evaluate_badges
from ..services.notifications import send_notification
from ..services.workout_plan import get_active_plan
from ..services.admin import list_users

settings = get_settings()
logger = logging.getLogger(__name__)

# Persist jobs in the database
jobstores = {
    'default': SQLAlchemyJobStore(url=settings.database_url, engine=engine)
}
scheduler = AsyncIOScheduler(
    jobstores=jobstores,
    timezone=settings.timezone
)

async def badge_evaluation_job():
    async with SessionLocal() as db:  # async session if available
        users = list_users(db)
        for user in users:
            try:
                evaluate_badges(db, user.id)
            except Exception:
                logger.exception("Error evaluating badges for user %s", user.id)

async def daily_reminder_job():
    async with SessionLocal() as db:
        users = list_users(db)
        for user in users:
            plan = get_active_plan(db, user.id)
            if not plan:
                continue
            payload = {
                "title": "Workout Reminder",
                "body": f"Don't forget your workout '{plan.name}' today!"
            }
            try:
                send_notification(db, user.id, 'workout_reminder', payload)
            except Exception:
                logger.exception("Error sending reminder to user %s", user.id)

def start_scheduler():
    # Dynamic cron from settings
    badge_trigger = CronTrigger.from_crontab(settings.badge_eval_cron, timezone=settings.timezone)
    reminder_trigger = CronTrigger.from_crontab(settings.daily_reminder_cron, timezone=settings.timezone)

    scheduler.add_job(
        badge_evaluation_job,
        trigger=badge_trigger,
        id='badge_evaluation',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    scheduler.add_job(
        daily_reminder_job,
        trigger=reminder_trigger,
        id='daily_reminder',
        replace_existing=True,
        max_instances=1,
        coalesce=True
    )
    scheduler.start()
    logger.info("Scheduler started with jobs: %s", scheduler.get_jobs())

def shutdown_scheduler():
    logger.info("Shutting down scheduler...")
    scheduler.shutdown(wait=False)

# Graceful shutdown on SIGINT/SIGTERM
signal.signal(signal.SIGINT, lambda *args: asyncio.get_event_loop().create_task(shutdown_scheduler()))
signal.signal(signal.SIGTERM, lambda *args: asyncio.get_event_loop().create_task(shutdown_scheduler()))
