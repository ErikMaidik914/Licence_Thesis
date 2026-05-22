import logging
from datetime import datetime
from typing import List, Dict

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.security import get_current_active_user
from ..core.metrics import Counter
from ..db.session import get_db
from ..db.models import Scan as ScanModel, User as UserModel
from ..services.recsys import map_equipment_to_muscle

router = APIRouter(tags=["users"])
logger = logging.getLogger("app.users")

# Metrics
profile_view_counter = Counter("user_profile_views_total", "Total profile views")
scan_fetch_counter = Counter("scan_fetch_total", "Total scan operations")
mapping_error_counter = Counter("equipment_mapping_errors_total", "Total equipment mapping errors")

class ScanOut(BaseModel):
    id: str = Field(..., description="Scan record ID")
    equipment: str = Field(..., description="Detected equipment name")
    detected_at: datetime = Field(..., alias="created_at", description="Timestamp of detection")

    class Config:
        orm_mode = True
        allow_population_by_field_name = True

class UserProfile(BaseModel):
    id: str
    username: str
    is_active: bool
    scans: List[ScanOut]
    by_muscle: Dict[str, List[ScanOut]]

    class Config:
        orm_mode = True

@router.get("/profile", response_model=UserProfile)
def get_profile(
    current_user: UserModel = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of scans to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max number of scans to return")
) -> UserProfile:
    profile_view_counter.inc()
    try:
        scans = (
            db.query(ScanModel)
              .filter(ScanModel.user_id == current_user.id)
              .order_by(ScanModel.created_at.desc())
              .offset(skip)
              .limit(limit)
              .all()
        )
        scan_fetch_counter.inc(len(scans))
    except Exception:
        logger.exception("Error fetching scans for user %s", current_user.id)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve scans")

    equipments = [scan.equipment for scan in scans]
    try:
        muscle_map = map_equipment_to_muscle(equipments)
    except Exception:
        mapping_error_counter.inc()
        logger.exception("Error mapping equipment to muscle for user %s", current_user.id)
        muscle_map = {equip: "Other" for equip in equipments}

    by_muscle: Dict[str, List[ScanModel]] = {}
    for scan in scans:
        muscle = muscle_map.get(scan.equipment, "Other")
        by_muscle.setdefault(muscle, []).append(scan)

    return UserProfile(
        id=str(current_user.id),
        username=current_user.username,
        is_active=current_user.is_active,
        scans=scans,
        by_muscle=by_muscle
    )
