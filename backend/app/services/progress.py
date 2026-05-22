import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Float
from sqlalchemy.exc import SQLAlchemyError

from ..db.models import ProgressEntry
from ..core.exceptions import BusinessException
from ..core.metrics import Counter

logger = logging.getLogger(__name__)

# Metrics
progress_log_counter = Counter("progress_log_total", "Total progress entries logged")
progress_error_counter = Counter("progress_errors_total", "Total errors in progress service")

trend_query_counter = Counter("progress_trend_queries_total", "Total progress trend queries")
trend_error_counter = Counter("progress_trend_errors_total", "Total errors in trend queries")


def log_progress(
    db: Session,
    user_id: Any,
    date: datetime,
    muscle_group: str,
    metric: str,
    value: Any,
    metadata: Optional[Dict[str, Any]] = None
) -> ProgressEntry:
    """
    Log a new progress entry for a user.
    Raises BusinessException on failure.
    """
    if not muscle_group or not metric:
        raise BusinessException("Muscle group and metric are required")
    entry = ProgressEntry(
        user_id=user_id,
        date=date or datetime.utcnow(),
        muscle_group=muscle_group.strip(),
        metric=metric.strip(),
        value=str(value),
        metadata=metadata or {}
    )
    try:
        db.add(entry)
        db.commit()
    except SQLAlchemyError:
        progress_error_counter.inc()
        logger.exception("Failed to log progress for user %s", user_id)
        raise BusinessException("Failed to log progress entry")
    db.refresh(entry)
    progress_log_counter.inc()
    logger.info("Logged progress entry %s for user %s", entry.id, user_id)
    return entry


def get_progress_entries(
    db: Session,
    user_id: Any,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    muscle_group: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[ProgressEntry]:
    """
    Fetch paginated progress entries for a user with optional filters.
    """
    query = db.query(ProgressEntry).filter(ProgressEntry.user_id == user_id)
    if start:
        query = query.filter(ProgressEntry.date >= start)
    if end:
        query = query.filter(ProgressEntry.date <= end)
    if muscle_group:
        query = query.filter(ProgressEntry.muscle_group == muscle_group)
    entries = (
        query.order_by(ProgressEntry.date.desc())
        .offset(max(skip, 0))
        .limit(min(limit, 1000))
        .all()
    )
    return entries


def get_trends(
    db: Session,
    user_id: Any,
    period: str = "week",
    date_range: Optional[Tuple[datetime, datetime]] = None,
    muscle_group: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Aggregate progress entries over time for trend analysis.
    Supported periods: 'day', 'week', 'month'
    """
    trend_query_counter.inc()
    trunc_map = {"day": "day", "week": "week", "month": "month"}
    if period not in trunc_map:
        trend_error_counter.inc()
        raise BusinessException(f"Unsupported period '{period}'")
    trunc = trunc_map[period]
    date_col = func.date_trunc(trunc, ProgressEntry.date).label("period")
    # Cast numeric values
    value_col = cast(ProgressEntry.value, Float)
    query = (
        db.query(
            date_col,
            func.count().label("entries"),
            func.sum(value_col).label("total")
        )
        .filter(ProgressEntry.user_id == user_id)
    )
    if muscle_group:
        query = query.filter(ProgressEntry.muscle_group == muscle_group)
    if date_range:
        start, end = date_range
        query = query.filter(ProgressEntry.date.between(start, end))
    try:
        rows = query.group_by(date_col).order_by(date_col).all()
    except SQLAlchemyError:
        trend_error_counter.inc()
        logger.exception("Error querying progress trends for user %s", user_id)
        raise BusinessException("Failed to retrieve progress trends")
    results: List[Dict[str, Any]] = []
    for row in rows:
        results.append({
            "period": row.period,
            "entries": int(row.entries),
            "total": float(row.total or 0.0)
        })
    return results
