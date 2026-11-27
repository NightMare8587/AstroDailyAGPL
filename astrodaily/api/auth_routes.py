from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..auth.google import GoogleIdentity, verify_google_token
from ..auth.tokens import create_access_token, hash_refresh_token, new_refresh_token
from ..config import get_settings
from ..db import get_db
from ..models import RefreshToken, User, utcnow
from ..ratelimit import limit
from .schemas import TokenOut, UserOut

router = APIRouter(prefix="/v1/auth", tags=["auth"],
                   dependencies=[Depends(limit("auth", "rate_limit_auth_per_minute"))])


class GoogleLoginIn(BaseModel):
    id_token: str


class RefreshIn(BaseModel):
    refresh_token: str


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _issue_tokens(db: Session, user: User) -> TokenOut:
    settings = get_settings()
    raw, token_hash = new_refresh_token()
    db.add(RefreshToken(
        user_id=user.id, token_hash=token_hash,
        expires_at=utcnow() + timedelta(days=settings.refresh_token_days),
    ))
    db.commit()
    return TokenOut(
        access_token=create_access_token(user.id), refresh_token=raw,
        expires_in=settings.access_token_minutes * 60, user=UserOut.from_user(user),
    )


def get_google_verifier():
    """Dependency so tests can replace real Google verification."""
    return verify_google_token


@router.post("/google", response_model=TokenOut)
def login_with_google(
    body: GoogleLoginIn, db: Session = Depends(get_db), verify=Depends(get_google_verifier),
) -> TokenOut:
    ident: GoogleIdentity = verify(body.id_token)
    user = db.scalar(select(User).where(User.google_sub == ident.sub))
    if user is None:
        user = User(google_sub=ident.sub, email=ident.email, email_verified=ident.email_verified,
                    name=ident.name, picture_url=ident.picture)
        db.add(user)
    else:
        user.email = ident.email
        user.email_verified = ident.email_verified
        user.name = ident.name or user.name
        user.picture_url = ident.picture or user.picture_url
    user.last_login_at = utcnow()
    db.commit()
    return _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenOut)
def refresh(body: RefreshIn, db: Session = Depends(get_db)) -> TokenOut:
    """Rotate: the presented refresh token is revoked and a new pair is issued.

    Presenting an already-revoked token means it may have been stolen, so every
    refresh token for that user is revoked.
    """
    token = db.scalar(select(RefreshToken).where(
        RefreshToken.token_hash == hash_refresh_token(body.refresh_token)))
    if token is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if token.revoked_at is not None:
        db.execute(update(RefreshToken)
                   .where(RefreshToken.user_id == token.user_id, RefreshToken.revoked_at.is_(None))
                   .values(revoked_at=utcnow()))
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token was already used")
    if _aware(token.expires_at) <= utcnow():
        raise HTTPException(status_code=401, detail="Refresh token expired")
    token.revoked_at = utcnow()
    user = db.get(User, token.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return _issue_tokens(db, user)


@router.post("/logout", status_code=204)
def logout(body: RefreshIn, db: Session = Depends(get_db)) -> None:
    token = db.scalar(select(RefreshToken).where(
        RefreshToken.token_hash == hash_refresh_token(body.refresh_token)))
    if token is not None and token.revoked_at is None:
        token.revoked_at = utcnow()
        db.commit()
