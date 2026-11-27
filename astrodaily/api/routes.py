from datetime import date as date_type
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import swisseph as swe
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import __version__
from .places_routes import PlaceOut
from ..calc.panchang import Element, Span, compute_panchang
from ..config import get_settings
from ..db import get_optional_db
from ..models import Place
from ..ratelimit import limit

router = APIRouter()

# The built-in Moshier ephemeris fails far outside this range; real use is well inside it.
MIN_DATE = date_type(1800, 1, 1)
MAX_DATE = date_type(2200, 12, 31)


class Named(BaseModel):
    en: str
    hi: str


class SpanOut(Named):
    start: datetime
    end: datetime
    nature: str | None = None


class ElementOut(Named):
    number: int
    ends_at: datetime
    paksha: str | None = None
    pada: int | None = None


class PanchangOut(BaseModel):
    date: date_type
    timezone: str
    sunrise: datetime
    sunset: datetime
    next_sunrise: datetime
    vara: Named
    tithi: ElementOut
    nakshatra: ElementOut
    yoga: ElementOut
    karana: ElementOut
    rahu_kaal: SpanOut
    gulika_kaal: SpanOut
    yamaganda: SpanOut
    abhijit: SpanOut
    choghadiya: list[SpanOut]
    place: PlaceOut | None = None
    ayanamsa_lahiri: float
    ayanamsa_note: str = "Lahiri (Chitrapaksha) sidereal; Swiss Ephemeris Moshier unless ephemeris files configured"


def _span(s: Span) -> SpanOut:
    return SpanOut(en=s.en, hi=s.hi, start=s.start, end=s.end, nature=s.nature)


def _element(e: Element) -> ElementOut:
    return ElementOut(number=e.number, en=e.en, hi=e.hi, ends_at=e.ends_at,
                      paksha=e.extra.get("paksha"), pada=e.extra.get("pada"))


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {"status": "ok", "version": __version__, "gemini_model": settings.gemini_model}


@router.get("/v1/panchang", response_model=PanchangOut,
            dependencies=[Depends(limit("panchang", "rate_limit_panchang_per_minute"))])
def panchang(
    date: date_type = Query(..., description="Local calendar date, YYYY-MM-DD"),
    place_id: int | None = Query(None, description="GeoNames place id from /v1/places/search. Use this or lat+lon."),
    lat: float | None = Query(None, ge=-66.0, le=66.0, description="Latitude, degrees north"),
    lon: float | None = Query(None, ge=-180.0, le=180.0, description="Longitude, degrees east"),
    tz: str | None = Query(None, description="IANA timezone name (default Asia/Kolkata, or the place's own)"),
    db: Session | None = Depends(get_optional_db),
) -> PanchangOut:
    if not MIN_DATE <= date <= MAX_DATE:
        raise HTTPException(status_code=422, detail=f"date must be between {MIN_DATE} and {MAX_DATE}")
    place = None
    if place_id is not None:
        if lat is not None or lon is not None:
            raise HTTPException(status_code=422, detail="Give either place_id or lat and lon, not both")
        if db is None:
            raise HTTPException(status_code=503, detail="Database is not configured")
        place = db.get(Place, place_id)
        if place is None:
            raise HTTPException(status_code=404, detail="Place not found")
        lat, lon = place.latitude, place.longitude
        tz = tz or place.timezone
    elif lat is None or lon is None:
        raise HTTPException(status_code=422, detail="Give place_id, or both lat and lon")
    tz = tz or "Asia/Kolkata"
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(status_code=422, detail=f"Unknown timezone: {tz}")
    try:
        p = compute_panchang(date, lat, lon, tz)
    except (ValueError, swe.Error) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return PanchangOut(
        date=p["date"], timezone=p["timezone"], sunrise=p["sunrise"], sunset=p["sunset"],
        next_sunrise=p["next_sunrise"], vara=Named(en=p["vara"][0], hi=p["vara"][1]),
        tithi=_element(p["tithi"]), nakshatra=_element(p["nakshatra"]),
        yoga=_element(p["yoga"]), karana=_element(p["karana"]),
        rahu_kaal=_span(p["rahu_kaal"]), gulika_kaal=_span(p["gulika_kaal"]),
        yamaganda=_span(p["yamaganda"]), abhijit=_span(p["abhijit"]),
        choghadiya=[_span(s) for s in p["choghadiya"]], ayanamsa_lahiri=p["ayanamsa"],
        place=PlaceOut.from_place(place) if place else None,
    )

