from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import get_settings
from .database import session_scope
from .models import User

password_hasher = PasswordHasher()
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return password_hasher.verify(hashed, password)
    except Exception:
        return False


def make_token(user: User) -> str:
    settings = get_settings()
    if len(settings.jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters")
    timestamp = datetime.now(timezone.utc)
    return jwt.encode({"sub": user.id, "role": user.role, "tenant": user.tenant_id, "iat": timestamp,
                       "exp": timestamp + timedelta(minutes=45), "iss": "careflow-nexus"},
                      settings.jwt_secret, algorithm="HS256")


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                 db: Session = Depends(session_scope)) -> User:
    if credentials is None:
        raise HTTPException(401, "Bearer token required")
    try:
        data = jwt.decode(credentials.credentials, get_settings().jwt_secret, algorithms=["HS256"],
                          issuer="careflow-nexus", options={"require": ["exp", "sub", "iss"]})
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, "Invalid or expired token") from None
    user = db.get(User, data["sub"])
    if user is None or user.tenant_id != data.get("tenant") or user.role != data.get("role"):
        raise HTTPException(401, "Session invalid")
    return user


def require_roles(*allowed: str):
    def check(user: User = Depends(current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(403, "Insufficient permission")
        return user
    return check
