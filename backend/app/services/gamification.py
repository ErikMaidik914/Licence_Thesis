import logging
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

from ..db.models import Badge, UserBadge, ProgressEntry
from ..core.config import get_settings
from ..core.exceptions import BusinessException
from ..core.metrics import Counter

logger = logging.getLogger(__name__)
settings = get_settings()

# Metrics
badge_eval_counter = Counter("badge_evaluations_total", "Total badge evaluations")
badge_award_counter = Counter("badges_awarded_total", "Total badges awarded")
badge_error_counter = Counter("badge_errors_total", "Total errors in badge service")

def evaluate_badges(db: Session, user_id: int) -> List[UserBadge]:
    """
    Evaluate all configured badge criteria and award any new badges.
    """
    badge_eval_counter.inc()
    awarded: List[UserBadge] = []
    criteria_list = settings.BADGE_CRITERIA  # must be a List[Dict]
    if not isinstance(criteria_list, list):
        raise BusinessException("Invalid badge criteria configuration")

    for crit in criteria_list:
        name = crit.get("badge_name")
        typ  = crit.get("type")
        metric = crit.get("metric")
        thresh = crit.get("threshold")
        if not name or not typ or thresh is None:
            logger.warning("Skipping malformed criterion: %r", crit)
            continue

        badge = db.query(Badge).filter_by(name=name).first()
        if not badge:
            logger.warning("Badge %r not found in DB", name)
            continue

        already = db.query(UserBadge).filter_by(
            user_id=user_id, badge_id=badge.id
        ).first()
        if already:
            continue

        try:
            qualifies = False
            if typ == "count":
                cnt = db.query(func.count(ProgressEntry.id))\
                        .filter(ProgressEntry.user_id == user_id)\
                        .scalar() or 0
                qualifies = cnt >= thresh
            elif typ == "aggregate":
                total = db.query(func.sum(func.cast(ProgressEntry.value, Float)))\
                          .filter(
                              ProgressEntry.user_id == user_id,
                              ProgressEntry.metric == metric
                          ).scalar() or 0
                qualifies = total >= thresh
            else:
                logger.error("Unknown criterion type %r", typ)
                continue

            if qualifies:
                awarded.append(_award_badge(db, user_id, badge.id))
        except SQLAlchemyError:
            badge_error_counter.inc()
            logger.exception("Error evaluating badge %r for user %s", name, user_id)

    return awarded

def _award_badge(db: Session, user_id: int, badge_id: int) -> UserBadge:
    """
    Atomically create and return a new UserBadge record.
    """
    now = datetime.utcnow()
    ub = UserBadge(user_id=user_id, badge_id=badge_id, awarded_at=now)
    try:
        with db.begin():
            db.add(ub)
    except SQLAlchemyError:
        badge_error_counter.inc()
        logger.exception("Failed to award badge %s to %s", badge_id, user_id)
        raise BusinessException("Could not award badge")
    db.refresh(ub)
    badge_award_counter.inc()
    logger.info("Awarded badge %s to user %s", badge_id, user_id)
    return ub

def get_user_badges(db: Session, user_id: int) -> List[UserBadge]:
    """
    List all badges a user has earned, most recent first.
    """
    try:
        return db.query(UserBadge)\
                 .filter_by(user_id=user_id)\
                 .order_by(UserBadge.awarded_at.desc())\
                 .all()
    except SQLAlchemyError:
        badge_error_counter.inc()
        logger.exception("Failed fetching badges for user %s", user_id)
        raise BusinessException("Could not fetch user badges")
