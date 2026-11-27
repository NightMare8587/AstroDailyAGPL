import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..db import get_db, get_optional_db
from ..models import User
from .tokens import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user_id = decode_access_token(creds.credentials)
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_optional_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session | None = Depends(get_optional_db),
) -> User | None:
    """The signed-in user if a valid token was sent, else None.

    An invalid or expired token does not fail the request here, because many endpoints work without
    a user. It sets request.state.bad_token so an endpoint that needs the user can answer 401.
    """
    request.state.bad_token = False
    if creds is None:
        return None
    try:
        user_id = decode_access_token(creds.credentials)
    except (jwt.PyJWTError, ValueError):
        request.state.bad_token = True
        return None
    if db is None:
        raise HTTPException(status_code=503, detail="Database is not configured")
    user = db.get(User, user_id)
    if user is None:
        request.state.bad_token = True
    return user
