from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db import get_db

hasher = PasswordHasher()
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, digest: str) -> bool:
    try:
        return hasher.verify(digest, password)
    except Exception:
        return False


def issue_token(user) -> str:
    return jwt.encode({"sub": str(user.id), "org_id": str(user.org_id), "role": user.role,
                       "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)},
                      settings.jwt_secret, algorithm="HS256")


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)):
    if not credentials:
        raise HTTPException(401, detail={"detail": "Authentication required", "code": "unauthorized"})
    try:
        claims = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"])
        user = db.get(__import__("app.models", fromlist=["User"]).User, claims["sub"])
    except Exception:
        user = None
    if user is None:
        raise HTTPException(401, detail={"detail": "Invalid or expired token", "code": "invalid_token"})
    return user


def require_role(*roles):
    def check(user=Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(403, detail={"detail": "This role cannot perform that action", "code": "forbidden"})
        return user
    return check
