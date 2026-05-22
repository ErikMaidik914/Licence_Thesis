# app/core/security.py

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
from jose import JWTError, ExpiredSignatureError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from sqlalchemy.orm import Session
import uuid
from pydantic import BaseModel

from ..db.session import get_db
from ..db.models import User, RevokedToken
from .config import get_settings

logger = logging.getLogger("app.security")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
ISSUER = settings.environment or None
AUDIENCE = settings.jwt_audience or None

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scopes={"user": "Normal user scope", "admin": "Admin scope"}
)

class TokenData(BaseModel):
    user_id: str
    scopes: List[str] = []
    jti: Optional[str] = None

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(
    subject: str,
    scopes: Optional[List[str]] = ['detect'],
    expires_delta: Optional[timedelta] = None
) -> str:
    now = datetime.utcnow()
    jti = uuid.uuid4().hex
    payload: Dict[str, Any] = {"sub": subject, "iat": now, "jti": jti}
    if ISSUER:
        payload["iss"] = ISSUER
    if AUDIENCE:
        payload["aud"] = AUDIENCE
    if scopes:
        payload["scopes"] = scopes
    logger.info("Creating access token for user %s with scopes %s", subject, scopes)
    payload["exp"] = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def _is_token_revoked(jti: str, db: Session) -> bool:
    return db.query(RevokedToken).filter_by(jti=jti).first() is not None

def decode_token(token: str, security_scopes: SecurityScopes) -> TokenData:
    credentials_exception.headers.update(
        {"WWW-Authenticate": f"Bearer scopes=\"{' '.join(security_scopes.scopes)}\""}
    )
    try:
        decode_args: Dict[str, Any] = {"key": SECRET_KEY, "algorithms": [ALGORITHM], "options": {"require": ["exp", "iat", "sub", "jti"]}}
        if AUDIENCE:
            decode_args["audience"] = AUDIENCE
        if ISSUER:
            decode_args["issuer"] = ISSUER
        payload = jwt.decode(**decode_args, token=token)
        user_id = payload.get("sub")
        token_scopes = payload.get("scopes", [])
        jti = payload.get("jti")
        if not user_id or not jti:
            raise credentials_exception
        return TokenData(user_id=user_id, scopes=token_scopes, jti=jti)
    except ExpiredSignatureError:
        logger.error("Expired token", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.error("decode_token failed: %s", e, exc_info=True)
        raise credentials_exception

def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    td = decode_token(token, security_scopes)
    if _is_token_revoked(td.jti, db):
        raise credentials_exception
    user = db.query(User).filter_by(id=td.user_id).first()
    if not user:
        raise credentials_exception
    for scope in security_scopes.scopes:
        if scope not in td.scopes:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": "Bearer"},
            )
    setattr(user, "scopes", td.scopes)
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

async def revoke_token(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    td = decode_token(token, SecurityScopes(scopes=[]))
    db.add(RevokedToken(jti=td.jti))
    db.commit()
