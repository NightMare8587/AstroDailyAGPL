"""Shared validation for anything that takes a birth date and a birth place."""
from dataclasses import dataclass
from datetime import date as date_type
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import Place

# The built-in Moshier ephemeris fails far outside this range; real use is well inside it.
MIN_DATE = date_type(1800, 1, 1)
MAX_DATE = date_type(2200, 12, 31)
DEFAULT_TZ = "Asia/Kolkata"


@dataclass
class Location:
    latitude: float
    longitude: float
    timezone: str            # IANA name, default or the place's own
    place: Place | None


def check_date(name: str, value: date_type) -> None:
    if not MIN_DATE <= value <= MAX_DATE:
        raise HTTPException(status_code=422, detail=f"{name} must be between {MIN_DATE} and {MAX_DATE}")


def place_label(place: Place | None) -> str | None:
    """'Name, District, State' for display and for the copy stored in a profile."""
    if place is None:
        return None
    return ", ".join(x for x in (place.name, place.district, place.state) if x)


def resolve_location(db: Session | None, place_id: int | None, lat: float | None, lon: float | None,
                     tz: str | None, what: str = "the birth place") -> Location:
    """Turn a place_id, or lat and lon, into a validated location. Raises HTTP errors for bad input."""
    place = None
    if place_id is not None:
        if lat is not None or lon is not None:
            raise HTTPException(status_code=422, detail="Give either place_id or lat and lon, not both")
        if db is None:
            raise HTTPException(status_code=503, detail="Database is not configured")
        place = db.get(Place, place_id)
        if place is None:
            raise HTTPException(status_code=404, detail="Place not found")
        lat, lon, tz = place.latitude, place.longitude, tz or place.timezone
    elif lat is None or lon is None:
        raise HTTPException(status_code=422, detail=f"Give {what}: place_id, or both lat and lon")
    tz = tz or DEFAULT_TZ
    try:
        ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        raise HTTPException(status_code=422, detail=f"Unknown timezone: {tz}")
    return Location(lat, lon, tz, place)
