import logging
from typing import List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.security import get_current_active_user
from ..core.exceptions import BusinessException, NotFoundException
from ..core.metrics import Counter
from ..db.session import get_db
from ..services.workout_plan import create_plan, get_active_plan, update_plan
from ..db.models import WorkoutPlan as WorkoutPlanModel, PlanPhase as PlanPhaseModel

router = APIRouter(tags=["plans"])
logger = logging.getLogger("app.plans")

# Metrics
plan_create_counter = Counter("plan_creations_total", "Total workout plans created")
plan_update_counter = Counter("plan_updates_total", "Total workout plans updated")
plan_read_counter = Counter("plan_reads_total", "Total workout plan reads")
plan_error_counter = Counter("plan_errors_total", "Total workout plan errors")

class PlanCreate(BaseModel):
    name: str = Field(..., max_length=100)
    goal: str = Field(..., max_length=50)
    start_date: datetime = Field(...)
    end_date: Optional[datetime] = None
    metadata: Optional[dict] = None

class PlanPhaseOut(BaseModel):
    id: str
    phase_name: str
    week_number: int
    details: dict

    class Config:
        orm_mode = True

class PlanOut(BaseModel):
    id: str
    name: str
    goal: str
    start_date: datetime
    end_date: Optional[datetime]
    metadata: Optional[dict]
    phases: List[PlanPhaseOut]

    class Config:
        orm_mode = True

class PlanUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    goal: Optional[str] = Field(None, max_length=50)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    metadata: Optional[dict] = None

@router.post("/", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def create_workout_plan(
    plan_in: PlanCreate,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> WorkoutPlanModel:
    if "plans" not in getattr(current_user, 'scopes', []):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    plan_create_counter.inc()
    try:
        plan = create_plan(
            db=db,
            user_id=current_user.id,
            name=plan_in.name.strip(),
            goal=plan_in.goal.strip(),
            start_date=plan_in.start_date,
            end_date=plan_in.end_date,
            metadata=plan_in.metadata
        )
        logger.info("Created plan %s for user %s", plan.id, current_user.id)
        return plan
    except BusinessException as e:
        plan_error_counter.inc()
        logger.warning("Plan creation failed: %s", e)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        plan_error_counter.inc()
        logger.exception("Unexpected error creating plan for user %s", current_user.id)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create workout plan")

@router.get("/active", response_model=PlanOut)
def read_active_plan(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> WorkoutPlanModel:
    if "plans" not in getattr(current_user, 'scopes', []):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    plan_read_counter.inc()
    plan = get_active_plan(db=db, user_id=current_user.id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No active workout plan found")
    return plan

@router.get("/history", response_model=List[PlanOut])
def read_plan_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[WorkoutPlanModel]:
    if "plans" not in getattr(current_user, 'scopes', []):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    plan_read_counter.inc()
    try:
        return (
            db.query(WorkoutPlanModel)
            .filter(WorkoutPlanModel.user_id == current_user.id)
            .order_by(WorkoutPlanModel.start_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    except Exception:
        plan_error_counter.inc()
        logger.exception("Error reading plan history for user %s", current_user.id)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to fetch plan history")

@router.put("/{plan_id}", response_model=PlanOut)
def modify_plan(
    plan_id: str,
    plan_in: PlanUpdate,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> WorkoutPlanModel:
    if "plans" not in getattr(current_user, 'scopes', []):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient scope")
    plan_read_counter.inc()
    try:
        plan = get_active_plan(db=db, user_id=current_user.id)
        if not plan or str(plan.id) != plan_id:
            raise NotFoundException("Workout plan not found or not active")
        updated = update_plan(db=db, plan_id=plan_id, updates=plan_in.dict(exclude_unset=True))
        plan_update_counter.inc()
        logger.info("Updated plan %s for user %s", plan_id, current_user.id)
        return updated
    except NotFoundException as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessException as e:
        plan_error_counter.inc()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        plan_error_counter.inc()
        logger.exception("Error updating plan %s for user %s", plan_id, current_user.id)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update workout plan")
