from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import logging

from ..core.security import get_current_active_user
from ..db.session import get_db
from ..services.gamification import evaluate_badges, get_user_badges
from ..db.models import UserBadge
from ..core.exceptions import BusinessException
from ..core.metrics import Counter

router = APIRouter(tags=["badges"])
logger = logging.getLogger("app.badges")

# Metrics
badge_eval_counter = Counter("badge_evaluations_total", "Total badge evaluations")
badge_award_counter = Counter("badges_awarded_total", "Total badges awarded")
badge_list_counter = Counter("user_badges_list_total", "Total badge listings per user")

class BadgeOut(BaseModel):
    id: str = Field(...)
    badge_id: str = Field(...)
    user_id: str = Field(...)
    awarded_at: str = Field(...)

    class Config:
        orm_mode = True

@router.post("/evaluate", response_model=List[BadgeOut])
def evaluate_user_badges(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[UserBadge]:
    if "user" not in current_user.scopes:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    badge_eval_counter.inc()
    try:
        awarded = evaluate_badges(db=db, user_id=current_user.id)
        badge_award_counter.inc(len(awarded))
    except BusinessException as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        logger.exception("Badge evaluation failed for user %s", current_user.id)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Evaluation error")
    return awarded

@router.get("/", response_model=List[BadgeOut])
def list_user_badges(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[UserBadge]:
    if "user" not in current_user.scopes:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    badge_list_counter.inc()
    try:
        return get_user_badges(db=db, user_id=current_user.id)
    except BusinessException as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Retrieval error")
