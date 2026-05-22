import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError

from ..db.models import User, WorkoutPlan, ProgressEntry
from ..core.config import get_settings
from ..core.exceptions import NotFoundException, BusinessException
from ..core.metrics import Counter

logger = logging.getLogger(__name__)
settings = get_settings()

# Metrics
user_list_counter = Counter("admin_user_list_total", "Total user list operations")
user_delete_counter = Counter("admin_user_deletions_total", "Total user deletions")
stats_query_counter = Counter("admin_stats_queries_total", "Total stats queries")
stats_error_counter = Counter("admin_stats_errors_total", "Total stats query errors")


def list_users(
    db: Session,
    skip: int = 0,
    limit: int = 100
) -> list[User]:
    user_list_counter.inc()
    if skip < 0 or limit <= 0:
        raise BusinessException("Invalid pagination parameters")
    return db.query(User).offset(skip).limit(limit).all()


def get_user_by_id(
    db: Session,
    user_id: Any
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise NotFoundException(f"User {user_id} not found")
    return user


def delete_user(
    db: Session,
    user_id: Any
) -> None:
    user = db.get(User, user_id)
    if not user:
        raise NotFoundException(f"User {user_id} not found")
    try:
        with db.begin():
            db.delete(user)
    except SQLAlchemyError:
        user_delete_counter.inc()
        logger.exception("Error deleting user %s", user_id)
        raise BusinessException("Could not delete user")
    user_delete_counter.inc()
    logger.info("Deleted user %s", user_id)


def get_stats(
    db: Session,
    since: datetime | None = None
) -> Dict[str, int]:
    stats_query_counter.inc()
    now = datetime.utcnow()
    since = since or (now - timedelta(days=7))
    try:
        total_users = db.query(func.count(User.id)).scalar() or 0
        active_plans = db.query(func.count(WorkoutPlan.id))\
            .filter(
                WorkoutPlan.start_date <= now,
                or_(WorkoutPlan.end_date == None, WorkoutPlan.end_date >= now)
            ).scalar() or 0
        new_users = db.query(func.count(User.id))\
            .filter(User.created_at >= since).scalar() or 0
        new_progress = db.query(func.count(ProgressEntry.id))\
            .filter(ProgressEntry.created_at >= since).scalar() or 0
        return {
            "total_users": total_users,
            "active_plans": active_plans,
            "new_users_last_week": new_users,
            "new_progress_entries_last_week": new_progress,
        }
    except SQLAlchemyError:
        stats_error_counter.inc()
        logger.exception("Error fetching stats since %s", since)
        raise BusinessException("Could not retrieve stats")
