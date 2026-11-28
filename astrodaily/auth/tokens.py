"""Session tokens: short-lived access JWT plus rotating opaque refresh token."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from ..config import get_settings

ALGORITHM = "HS256"


def create_access_token(user_id: uuid.UUID) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "typ": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.require_jwt_secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID:
    """Return the user id, or raise jwt.PyJWTError / ValueError if invalid."""
    payload = jwt.decode(
        token, get_settings().require_jwt_secret(), algorithms=[ALGORITHM],
        options={"require": ["exp", "sub"]},
    )
    if payload.get("typ") != "access":
        raise ValueError("wrong token type")
    return uuid.UUID(payload["sub"])


def new_refresh_token() -> tuple[str, str]:
    """(raw token to send to the client, sha256 hash to store)."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_widget_token(user_id: uuid.UUID) -> tuple[str, datetime]:
    """A long-lived token that can do exactly one thing: read the home-screen widget card. It is separate from the
    session so a background job on the phone never touches the rotating refresh token. Returns (token, expires)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=settings.widget_token_days)
    payload = {
        "sub": str(user_id),
        "typ": "widget",
        "iat": now,
        "t": int(now.timestamp() * 1_000_000),  # issue time in microseconds: a sign-out revokes tokens issued before it
        "exp": exp,
    }
    return jwt.encode(payload, settings.require_jwt_secret(), algorithm=ALGORITHM), exp


def decode_widget_token(token: str) -> tuple[uuid.UUID, int]:
    """(user id, issue time in microseconds), or raise jwt.PyJWTError / ValueError. Access tokens are refused."""
    payload = jwt.decode(
        token, get_settings().require_jwt_secret(), algorithms=[ALGORITHM],
        options={"require": ["exp", "sub", "t"]},
    )
    if payload.get("typ") != "widget":
        raise ValueError("wrong token type")
    return uuid.UUID(payload["sub"]), int(payload["t"])
