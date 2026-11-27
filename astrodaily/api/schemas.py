import uuid
from typing import Literal

from pydantic import BaseModel

from ..models import User


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    picture_url: str | None
    language: str
    consent_version: str | None

    @classmethod
    def from_user(cls, user: User) -> "UserOut":
        return cls(id=user.id, email=user.email, name=user.name, picture_url=user.picture_url,
                   language=user.language, consent_version=user.consent_version)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserOut
