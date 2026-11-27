from datetime import date as date_type
from datetime import datetime, timezone
from datetime import time as time_type
from typing import Literal

import swisseph as swe
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..calc import dasha, names, zodiac
from ..calc.kundli import compute_chart, names_pair, resolve_birth_moment
from ..db import get_optional_db
from ..ratelimit import limit
from .birth import Location, check_date, resolve_location
from .schemas import PlaceOut

router = APIRouter(prefix="/v1/kundli", tags=["kundli"],
                   dependencies=[Depends(limit("kundli", "rate_limit_panchang_per_minute"))])


class KundliIn(BaseModel):
    date: date_type = Field(description="Birth date (local), YYYY-MM-DD")
    time: time_type = Field(description="Birth time (local), HH:MM or HH:MM:SS")
    place_id: int | None = Field(None, description="Birth place from /v1/places/search. Use this or lat and lon.")
    lat: float | None = Field(None, ge=-66.0, le=66.0)
    lon: float | None = Field(None, ge=-180.0, le=180.0)
    tz: str | None = Field(None, description="IANA timezone; default Asia/Kolkata, or the place's own")
    utc_offset_minutes: int | None = Field(None, ge=-840, le=840,
                                           description="Overrides tz. Use it to confirm the offset for old or unusual births.")
    node: Literal["mean", "true"] = "mean"
    as_of: date_type | None = Field(None, description="Date for the running dasha; default today")


class Named(BaseModel):
    en: str
    hi: str


class SignOut(Named):
    number: int


class PlanetOut(BaseModel):
    key: str
    name: Named
    longitude: float
    sign: SignOut
    degree_in_sign: float
    nakshatra: SignOut
    pada: int
    house: int
    retrograde: bool
    dignity: str | None
    navamsa_sign: SignOut


class LagnaOut(BaseModel):
    longitude: float
    sign: SignOut
    degree_in_sign: float
    nakshatra: SignOut
    pada: int
    navamsa_sign: SignOut


class HouseOut(BaseModel):
    house: int
    sign: SignOut
    lord: Named
    planets: list[str]


class PeriodOut(BaseModel):
    lord: Named
    start: datetime
    end: datetime


class MahadashaOut(PeriodOut):
    antardashas: list[PeriodOut]


class CurrentDashaOut(BaseModel):
    mahadasha: PeriodOut
    antardasha: PeriodOut
    pratyantardasha: PeriodOut


class BalanceOut(BaseModel):
    lord: Named
    years_total: int
    fraction_elapsed: float
    years_remaining: float


class DashaOut(BaseModel):
    system: str
    year_length_days: float
    balance_at_birth: BalanceOut
    mahadashas: list[MahadashaOut]
    as_of: datetime
    current: CurrentDashaOut | None


class BirthOut(BaseModel):
    local_datetime: datetime
    utc_datetime: datetime
    timezone: str
    utc_offset_minutes: int
    latitude: float
    longitude: float
    place: PlaceOut | None


class KundliOut(BaseModel):
    birth: BirthOut
    warnings: list[str]
    ayanamsa_lahiri: float
    node: str
    lagna: LagnaOut
    planets: list[PlanetOut]
    houses: list[HouseOut]
    dasha: DashaOut


def _sign(n: int) -> SignOut:
    return SignOut(number=n, **names_pair(zodiac.SIGNS[n - 1]))


def _nak(n: int) -> SignOut:
    return SignOut(number=n, **names_pair(names.NAKSHATRA[n - 1]))


def _lord(key: str) -> Named:
    return Named(**names_pair(zodiac.PLANET_NAMES[key]))


def _period(p: dict) -> dict:
    return {**p, "lord": _lord(p["lord"])}


def build_kundli(*, birth_date: date_type, birth_time: time_type, location: Location,
                 utc_offset_minutes: int | None, node: str, as_of_date: date_type | None) -> KundliOut:
    """Calculate a chart for already-validated inputs. Shared by the stateless and saved-profile endpoints."""
    try:
        birth = resolve_birth_moment(birth_date, birth_time, location.timezone, utc_offset_minutes)
        as_of = None
        if as_of_date is not None:
            as_of = datetime.combine(as_of_date, time_type(12, 0), tzinfo=birth.tz).astimezone(timezone.utc)
        chart = compute_chart(birth, location.latitude, location.longitude, node, as_of)
    except (ValueError, OverflowError, swe.Error) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    place = location.place
    tz_label = location.timezone if utc_offset_minutes is None else f"UTC{birth.utc_offset_minutes:+d}min"
    d = chart["dasha"]
    return KundliOut(
        birth=BirthOut(local_datetime=birth.local, utc_datetime=birth.utc, timezone=tz_label,
                       utc_offset_minutes=birth.utc_offset_minutes, latitude=location.latitude,
                       longitude=location.longitude, place=PlaceOut.from_place(place) if place else None),
        warnings=birth.warnings,
        ayanamsa_lahiri=chart["ayanamsa"],
        node=node,
        lagna=LagnaOut(
            longitude=chart["lagna"]["longitude"], sign=_sign(chart["lagna"]["sign"]),
            degree_in_sign=chart["lagna"]["degree_in_sign"], nakshatra=_nak(chart["lagna"]["nakshatra"]),
            pada=chart["lagna"]["pada"], navamsa_sign=_sign(chart["lagna"]["navamsa_sign"])),
        planets=[PlanetOut(
            key=p["key"], name=Named(**p["name"]), longitude=p["longitude"], sign=_sign(p["sign"]),
            degree_in_sign=p["degree_in_sign"], nakshatra=_nak(p["nakshatra"]), pada=p["pada"],
            house=p["house"], retrograde=p["retrograde"], dignity=p["dignity"],
            navamsa_sign=_sign(p["navamsa_sign"])) for p in chart["planets"]],
        houses=[HouseOut(house=h["house"], sign=_sign(h["sign"]), lord=_lord(h["lord"]), planets=h["planets"])
                for h in chart["houses"]],
        dasha=DashaOut(
            system=d["system"], year_length_days=d["year_length_days"],
            balance_at_birth=BalanceOut(**{**d["balance_at_birth"], "lord": _lord(d["balance_at_birth"]["lord"])}),
            mahadashas=[MahadashaOut(**{**_period(m), "antardashas": [_period(a) for a in m["antardashas"]]})
                        for m in d["mahadashas"]],
            as_of=d["as_of"],
            current=CurrentDashaOut(**{k: _period(v) for k, v in d["current"].items()}) if d["current"] else None),
    )


@router.post("", response_model=KundliOut)
def kundli(body: KundliIn, db: Session | None = Depends(get_optional_db)) -> KundliOut:
    """Calculate a birth chart. Nothing is stored."""
    check_date("date", body.date)
    if body.as_of is not None:
        check_date("as_of", body.as_of)
    location = resolve_location(db, body.place_id, body.lat, body.lon, body.tz)
    return build_kundli(birth_date=body.date, birth_time=body.time, location=location,
                        utc_offset_minutes=body.utc_offset_minutes, node=body.node, as_of_date=body.as_of)
