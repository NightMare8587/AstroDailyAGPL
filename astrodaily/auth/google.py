"""Verify a Google ID token sent by the Flutter app (google_sign_in)."""
from dataclasses import dataclass

from fastapi import HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from ..config import get_settings


@dataclass
class GoogleIdentity:
    sub: str
    email: str
    email_verified: bool
    name: str | None
    picture: str | None


def verify_google_token(token: str) -> GoogleIdentity:
    """Check signature, expiry, issuer and audience. Raises HTTP 401 if invalid."""
    client_ids = get_settings().google_client_id_list
    if not client_ids:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")
    try:
        info = google_id_token.verify_oauth2_token(
            token, google_requests.Request(), audience=client_ids
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    email = info.get("email")
    if not info.get("sub") or not email:
        raise HTTPException(status_code=401, detail="Google token has no email")
    if not info.get("email_verified", False):
        raise HTTPException(status_code=401, detail="Google email is not verified")
    return GoogleIdentity(
        sub=info["sub"], email=email, email_verified=True,
        name=info.get("name"), picture=info.get("picture"),
    )
