from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.security import get_current_active_user
from ..core.config import get_settings
from ..core.exceptions import NotFoundException, BusinessException
from ..db.session import get_db
from ..services.admin import list_users, get_user_by_id, delete_user, get_stats
from ..db.models import User

settings = get_settings()

# Role-based admin dependency
async def admin_required(
    current_user: User = Depends(get_current_active_user)
) -> User:
    if "admin" not in getattr(current_user, "roles", []):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user

router = APIRouter(
    tags=["admin"],
    responses={404: {"description": "Not Found"}, 403: {"description": "Forbidden"}}
)

class UserOut(BaseModel):
    id: str
    username: str
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True

class StatsOut(BaseModel):
    total_users: int
    active_plans: int
    new_users_last_week: int
    new_progress_entries_last_week: int

@router.get(
    "/users",
    response_model=List[UserOut],
    status_code=status.HTTP_200_OK,
    summary="List users",
    description="Retrieve a paginated list of users."
)
def api_list_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max number of users to return"),
    admin: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    try:
        return list_users(db=db, skip=skip, limit=limit)
    except BusinessException as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get(
    "/users/{user_id}",
    response_model=UserOut,
    status_code=status.HTTP_200_OK,
    summary="Get user",
    description="Retrieve a single user by ID."
)
def api_get_user(
    user_id: str,
    admin: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    try:
        return get_user_by_id(db=db, user_id=user_id)
    except NotFoundException:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Delete a user and related data."
)
def api_delete_user(
    user_id: str,
    admin: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    try:
        delete_user(db=db, user_id=user_id)
    except NotFoundException:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    return None

@router.get(
    "/stats",
    response_model=StatsOut,
    status_code=status.HTTP_200_OK,
    summary="Get stats",
    description="Retrieve application-wide statistics since a given datetime."
)
def api_get_stats(
    since: Optional[datetime] = Query(
        None,
        description="Start datetime for stats (ISO 8601)"
    ),
    admin: User = Depends(admin_required),
    db: Session = Depends(get_db)
):
    try:
        return get_stats(db=db, since=since)
    except BusinessException as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve stats"
        )
