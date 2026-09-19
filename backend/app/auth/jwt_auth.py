"""JWT authentication (single-tenant)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import text

from backend.app.config import get_settings
from backend.app.database import get_engine

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(username: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def ensure_default_user() -> None:
    settings = get_settings()
    engine = get_engine()
    hashed = hash_password(settings.admin_password)
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT password_hash FROM app_users WHERE username = :u"),
            {"u": settings.admin_username},
        ).fetchone()
        if row is None:
            conn.execute(
                text("INSERT INTO app_users (username, password_hash) VALUES (:u, :p)"),
                {"u": settings.admin_username, "p": hashed},
            )
        elif not verify_password(settings.admin_password, row[0]):
            conn.execute(
                text("UPDATE app_users SET password_hash = :p WHERE username = :u"),
                {"u": settings.admin_username, "p": hashed},
            )


def authenticate_user(username: str, password: str) -> bool:
    settings = get_settings()
    if username != settings.admin_username:
        return False
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT password_hash FROM app_users WHERE username = :u AND is_active = TRUE"),
            {"u": username},
        ).fetchone()
    if not row:
        return False
    return verify_password(password, row[0])


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
