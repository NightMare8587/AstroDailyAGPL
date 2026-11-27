from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..models import Place, PlaceName
from .normalize import normalize

MIN_QUERY_LENGTH = 2


def search_places(db: Session, query: str, limit: int = 10) -> list[Place]:
    """Prefix search over place names (English, alternate and Hindi). Biggest places first."""
    q = normalize(query)
    if len(q) < MIN_QUERY_LENGTH:
        return []
    matching = select(PlaceName.place_id).where(PlaceName.name_norm.startswith(q, autoescape=True))
    # Also match the Hindi name kept on the place itself: places imported before the importer fix may lack a Hindi
    # row in place_names (the name cap cut it off for places with many alternate names).
    stmt = (
        select(Place)
        .where(or_(Place.id.in_(matching), Place.name_hi.startswith(q, autoescape=True)))
        .order_by(Place.population.desc(), Place.name, Place.id)
        .limit(limit)
    )
    return list(db.scalars(stmt))
