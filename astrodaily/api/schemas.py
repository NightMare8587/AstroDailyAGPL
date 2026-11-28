import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel

from ..models import Place, User


class PlaceOut(BaseModel):
    id: int
    name: str
    name_hi: str | None
    state: str | None
    district: str | None
    country_code: str
    latitude: float
    longitude: float
    population: int
    timezone: str

    @classmethod
    def from_place(cls, p: Place) -> "PlaceOut":
        return cls(id=p.id, name=p.name, name_hi=p.name_hi, state=p.state, district=p.district,
                   country_code=p.country_code, latitude=p.latitude, longitude=p.longitude,
                   population=p.population, timezone=p.timezone)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    # True once the setup page is done: names, date of birth and a birth profile (gender is optional).
    onboarded: bool = False
    picture_url: str | None
    language: str
    consent_version: str | None
    home_place: PlaceOut | None = None

    @classmethod
    def from_user(cls, user: User) -> "UserOut":
        return cls(id=user.id, email=user.email, name=user.name, first_name=user.first_name,
                   last_name=user.last_name, date_of_birth=user.date_of_birth, gender=user.gender,
                   onboarded=bool(user.first_name and user.last_name and user.date_of_birth and user.profiles),
                   picture_url=user.picture_url,
                   language=user.language, consent_version=user.consent_version,
                   home_place=PlaceOut.from_place(user.home_place) if user.home_place else None)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserOut
