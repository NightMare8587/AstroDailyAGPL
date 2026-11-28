"""Work out a Moon sign from birth details, without saving anything. The setup page uses it when the birth time is
unknown, to find out whether the person has to choose between two signs."""
from datetime import date as date_type
from datetime import time as time_type

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user
from ..calc import moonsign, namesyl
from ..db import get_db
from ..models import User
from ..ratelimit import limit
from .birth import check_date, resolve_location

router = APIRouter(prefix="/v1/moon-sign", tags=["moon-sign"],
                   dependencies=[Depends(limit("moonsign", "rate_limit_default_per_minute"))])


class MoonSignIn(BaseModel):
    birth_date: date_type
    birth_time: time_type | None = None  # null when not known
    place_id: int | None = None
    lat: float | None = Field(None, ge=-66.0, le=66.0)
    lon: float | None = Field(None, ge=-180.0, le=180.0)
    tz: str | None = None
    first_name: str | None = Field(None, max_length=40)  # only used for the name hint


class NameHint(BaseModel):
    syllable: str
    sign: int
    nakshatra: int
    pada: int


class MoonSignOut(BaseModel):
    time_known: bool
    candidates: list[int]        # the possible Moon signs (one, or two when the Moon changed sign that day)
    moon_sign: int | None        # set when the answer is certain
    needs_choice: bool           # true when there are two candidates: the person picks one
    nakshatra: int | None = None  # only with a birth time
    pada: int | None = None
    name_hint: NameHint | None = None  # which of the two signs the first name points to, when it points to one


@router.post("", response_model=MoonSignOut)
def moon_sign(body: MoonSignIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MoonSignOut:
    check_date("birth_date", body.birth_date)
    loc = resolve_location(db, body.place_id, body.lat, body.lon, body.tz)
    try:
        if body.birth_time is not None:
            m = moonsign.moon_at_birth(body.birth_date, body.birth_time, loc.timezone, None)
            return MoonSignOut(time_known=True, candidates=[m.sign], moon_sign=m.sign, needs_choice=False,
                               nakshatra=m.nakshatra, pada=m.pada)
        cands = moonsign.candidate_signs(body.birth_date, loc.timezone, None)
    except (ValueError, OverflowError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    hint = namesyl.hint(body.first_name, cands) if len(cands) == 2 else None
    return MoonSignOut(time_known=False, candidates=cands, moon_sign=cands[0] if len(cands) == 1 else None,
                       needs_choice=len(cands) == 2, name_hint=NameHint(**hint) if hint else None)
