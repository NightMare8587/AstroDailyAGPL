from datetime import date as date_type
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .. import __version__
from ..calc.panchang import Element, Span, compute_panchang
from ..config import get_settings

router = APIRouter()


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


@router.get("/v1/panchang", response_model=PanchangOut)
def panchang(
    date: date_type = Query(..., description="Local calendar date, YYYY-MM-DD"),
    lat: float = Query(..., ge=-66.0, le=66.0, description="Latitude, degrees north"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude, degrees east"),
    tz: str = Query("Asia/Kolkata", description="IANA timezone name"),
) -> PanchangOut:
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(status_code=422, detail=f"Unknown timezone: {tz}")
    try:
        p = compute_panchang(date, lat, lon, tz)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return PanchangOut(
        date=p["date"], timezone=p["timezone"], sunrise=p["sunrise"], sunset=p["sunset"],
        next_sunrise=p["next_sunrise"], vara=Named(en=p["vara"][0], hi=p["vara"][1]),
        tithi=_element(p["tithi"]), nakshatra=_element(p["nakshatra"]),
        yoga=_element(p["yoga"]), karana=_element(p["karana"]),
        rahu_kaal=_span(p["rahu_kaal"]), gulika_kaal=_span(p["gulika_kaal"]),
        yamaganda=_span(p["yamaganda"]), abhijit=_span(p["abhijit"]),
        choghadiya=[_span(s) for s in p["choghadiya"]], ayanamsa_lahiri=p["ayanamsa"],
    )
