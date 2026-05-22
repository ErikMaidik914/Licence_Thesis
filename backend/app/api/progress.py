import logging
from datetime import datetime
from typing import List, Optional, Tuple, Any

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.security import get_current_active_user
from ..core.exceptions import BusinessException
from ..core.metrics import Counter
from ..db.session import get_db
from ..services.progress import log_progress, get_progress_entries, get_trends
from ..db.models import ProgressEntry as ProgressEntryModel

router = APIRouter(tags=["progress"])
logger = logging.getLogger("app.progress")

# Metrics
progress_log_counter = Counter("progress_entries_logged_total", "Total progress entries logged")
progress_list_counter = Counter("progress_entries_listed_total", "Total progress entries listed")
trends_counter = Counter("progress_trends_total", "Total progress trend queries")
progress_error_counter = Counter("progress_errors_total", "Total progress service errors")

class ProgressEntryCreate(BaseModel):
    date: datetime = Field(default_factory=datetime.utcnow, description="Date/time of the entry")
    muscle_group: str = Field(..., max_length=50, description="Target muscle group")
    metric: str = Field(..., max_length=50, description="Metric name")
    value: float = Field(..., description="Numeric metric value")
    metadata: Optional[dict] = Field(None, description="Additional JSON metadata")

class ProgressEntryOut(BaseModel):
    id: str
    date: datetime
    muscle_group: str
    metric: str
    value: float
    metadata: Optional[dict]

    class Config:
        orm_mode = True

class TrendOut(BaseModel):
    period: datetime
    entries: int
    total: float

@router.post("/", response_model=ProgressEntryOut, status_code=status.HTTP_201_CREATED)
def create_progress_entry(
    entry_in: ProgressEntryCreate,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> ProgressEntryModel:
    if "progress" not in getattr(current_user, 'scopes', []):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    progress_log_counter.inc()
    try:
        entry = log_progress(
            db=db,
            user_id=current_user.id,
            date=entry_in.date,
            muscle_group=entry_in.muscle_group.strip(),
            metric=entry_in.metric.strip(),
            value=entry_in.value,
            metadata=entry_in.metadata
        )
        logger.info("Logged progress entry %s for user %s", entry.id, current_user.id)
        return entry
    except BusinessException as e:
        progress_error_counter.inc()
        logger.warning("Progress log business error: %s", e)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        progress_error_counter.inc()
        logger.exception("Error logging progress for user %s", current_user.id)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to log progress entry")

@router.get("/", response_model=List[ProgressEntryOut], status_code=status.HTTP_200_OK)
def list_progress_entries(
    start: Optional[datetime] = Query(None, description="Filter start date"),
    end: Optional[datetime] = Query(None, description="Filter end date"),
    muscle_group: Optional[str] = Query(None, max_length=50),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[ProgressEntryModel]:
    if "progress" not in getattr(current_user, 'scopes', []):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    progress_list_counter.inc()
    try:
        entries = get_progress_entries(
            db=db,
            user_id=current_user.id,
            start=start,
            end=end,
            muscle_group=muscle_group
        )
        return entries[skip: skip + limit]
    except BusinessException as e:
        progress_error_counter.inc()
        logger.warning("Progress list business error: %s", e)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        progress_error_counter.inc()
        logger.exception("Error fetching progress entries for user %s", current_user.id)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch progress entries")

@router.get("/trends", response_model=List[TrendOut], status_code=status.HTTP_200_OK)
def progress_trends(
    period: str = Query("week", regex="^(day|week|month)$"),
    from_date: Optional[datetime] = Query(None, alias="from"),
    to_date: Optional[datetime] = Query(None, alias="to"),
    muscle_group: Optional[str] = Query(None, max_length=50),
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[TrendOut]:
    if "progress" not in getattr(current_user, 'scopes', []):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    trends_counter.inc()
    try:
        date_range: Optional[Tuple[datetime, datetime]] = None
        if from_date and to_date:
            date_range = (from_date, to_date)
        return get_trends(
            db=db,
            user_id=current_user.id,
            period=period,
            date_range=date_range,
            muscle_group=muscle_group
        )
    except ValueError as e:
        progress_error_counter.inc()
        logger.warning("Invalid trend parameters: %s", e)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except BusinessException as e:
        progress_error_counter.inc()
        logger.warning("Trend business error: %s", e)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        progress_error_counter.inc()
        logger.exception("Error fetching trends for user %s", current_user.id)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve progress trends")
