import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from ..db.models import WorkoutPlan, PlanPhase
from ..services.recsys import recommend_workouts
from ..core.exceptions import NotFoundException, BusinessException
from ..core.metrics import Counter

logger = logging.getLogger(__name__)

# Metrics
plan_creation_counter = Counter("plan_creation_total", "Total workout plans created")
plan_update_counter = Counter("plan_updates_total", "Total workout plans updated")
plan_error_counter = Counter("plan_errors_total", "Total errors in plan service")


def create_plan(
    db: Session,
    user_id: Any,
    name: str,
    goal: str,
    start_date: datetime,
    end_date: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> WorkoutPlan:
    """
    Create a new WorkoutPlan with optional metadata and auto-generated phases.
    Raises BusinessException on failure.
    """
    if not name:
        raise BusinessException("Plan name must be provided")
    if start_date and end_date and end_date < start_date:
        raise BusinessException("End date must be after start date")
    plan = WorkoutPlan(
        user_id=user_id,
        name=name.strip(),
        goal=goal.strip(),
        start_date=start_date,
        end_date=end_date,
        metadata=metadata or {}
    )
    try:
        with db.begin():
            db.add(plan)
            db.flush()  # populate plan.id
            # Auto-generate phases
            suggestions = []
            try:
                suggestions = recommend_workouts([goal], top_n=4)
            except Exception as e:
                logger.warning("Recommendation failed: %s", e)
            phases: List[PlanPhase] = []
            for idx, title in enumerate(suggestions, start=1):
                phases.append(
                    PlanPhase(
                        plan_id=plan.id,
                        phase_name=title,
                        week_number=idx,
                        details={"exercises": []}
                    )
                )
            if phases:
                db.add_all(phases)
    except IntegrityError as e:
        plan_error_counter.inc()
        logger.error("WorkoutPlan name conflict for user %s: %s", user_id, e)
        raise BusinessException("A plan with that name already exists")
    except SQLAlchemyError as e:
        plan_error_counter.inc()
        logger.exception("Database error creating plan for user %s", user_id)
        raise BusinessException("Failed to create workout plan")
    db.refresh(plan)
    plan_creation_counter.inc()
    logger.info("Created WorkoutPlan %s for user %s", plan.id, user_id)
    return plan


def get_active_plan(
    db: Session,
    user_id: Any,
    as_of: Optional[datetime] = None
) -> Optional[WorkoutPlan]:
    """
    Return the active WorkoutPlan for a user, if any.
    """
    now = as_of or datetime.utcnow()
    plan = (
        db.query(WorkoutPlan)
        .filter(
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.start_date <= now,
            ((WorkoutPlan.end_date == None) | (WorkoutPlan.end_date >= now))
        )
        .order_by(WorkoutPlan.start_date.desc())
        .first()
    )
    if plan:
        logger.debug("Active plan %s for user %s", plan.id, user_id)
    else:
        logger.debug("No active plan for user %s", user_id)
    return plan


def update_plan(
    db: Session,
    plan_id: Any,
    updates: Dict[str, Any]
) -> WorkoutPlan:
    """
    Apply partial updates to a WorkoutPlan.
    Raises NotFoundException if plan not found.
    """
    plan = db.get(WorkoutPlan, plan_id)
    if not plan:
        logger.warning("WorkoutPlan %s not found", plan_id)
        raise NotFoundException(f"WorkoutPlan {plan_id} not found")
    # Prevent updating immutable fields
    immutable = {"id", "user_id", "created_at", "updated_at"}
    for field, value in updates.items():
        if field in immutable:
            logger.warning("Attempt to update immutable field %s on plan %s", field, plan_id)
            continue
        if hasattr(plan, field) and value is not None:
            setattr(plan, field, value)
    try:
        with db.begin():
            db.add(plan)
    except SQLAlchemyError as e:
        plan_error_counter.inc()
        logger.exception("Error updating plan %s", plan_id)
        raise BusinessException("Failed to update workout plan")
    db.refresh(plan)
    plan_update_counter.inc()
    logger.info("Updated WorkoutPlan %s", plan_id)
    return plan
