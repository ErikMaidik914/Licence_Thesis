from typing import List, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import logging
from datetime import datetime

from ..db.session import get_db
from ..db.models import User
from ..core.security import verify_password, get_password_hash, create_access_token
from ..core.exceptions import BusinessException
from ..core.metrics import Counter
from ..core.config import get_settings
from pydantic import BaseModel, Field, EmailStr, ConfigDict

settings = get_settings()
router = APIRouter(tags=["auth"],
                   responses={400: {"description": "Bad Request"},
                              401: {"description": "Unauthorized"}})
logger = logging.getLogger("app.auth")

# Metrics
register_counter = Counter("auth_register_total", "Total user registrations")
login_counter = Counter("auth_login_total", "Total login attempts")
login_fail_counter = Counter("auth_login_fail_total", "Total failed logins")

class Token(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type, always 'bearer'")

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8)

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:         UUID
    username:   str
    email:      EmailStr
    is_active:  bool
    created_at: datetime

@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new user account with a unique username and email."
)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    request: Request = None
) -> UserOut:
    username = user_in.username.strip().lower()
    email = user_in.email.strip().lower()
    if db.query(User).filter((User.username == username) | (User.email == email)).first():
        logger.info("Registration conflict for %s", username)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered"
        )

    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash(user_in.password)
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        logger.exception("Registration error for %s: %s", username, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user"
        )

    register_counter.inc()
    logger.info("User registered: %s", user.id)
    return user

@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Authenticate a user and issue a token",
    description="Validates credentials and returns a JWT for authenticated requests."
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    login_counter.inc()
    user = db.query(User).filter_by(username=form_data.username.strip().lower()).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        login_fail_counter.inc()
        logger.warning("Invalid login for %s", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )
    if not user.is_active:
        logger.warning("Inactive user login attempt: %s", user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive account"
        )
    access_token = create_access_token(
        subject=str(user.id),
        scopes=['user', 'detect', 'progress', 'plans', 'notifications'],
    )
    logger.info("User logged in: %s", user.id)
    return {"access_token": access_token, "token_type": "bearer"}
