from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Place
from ..places.search import MIN_QUERY_LENGTH, search_places
from ..ratelimit import limit

router = APIRouter(prefix="/v1/places", tags=["places"],
                   dependencies=[Depends(limit("places", "rate_limit_default_per_minute"))])

ATTRIBUTION = "Place data from GeoNames (https://www.geonames.org), licensed CC BY 4.0"


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


class PlaceSearchOut(BaseModel):
    results: list[PlaceOut]
    attribution: str = ATTRIBUTION


@router.get("/search", response_model=PlaceSearchOut)
def search(
    q: str = Query(..., max_length=100, description=f"Start of a place name, English or Hindi (min {MIN_QUERY_LENGTH} letters)"),
    limit_: int = Query(10, alias="limit", ge=1, le=20),
    db: Session = Depends(get_db),
) -> PlaceSearchOut:
    return PlaceSearchOut(results=[PlaceOut.from_place(p) for p in search_places(db, q, limit_)])


@router.get("/{place_id}", response_model=PlaceOut)
def get_place(place_id: int, db: Session = Depends(get_db)) -> PlaceOut:
    place = db.get(Place, place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return PlaceOut.from_place(place)
