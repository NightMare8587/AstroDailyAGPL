"""Push notification settings and device registration."""
import uuid
from datetime import datetime, time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user
from ..config import get_settings
from ..db import get_db
from ..models import DeviceToken, NotificationPrefs, User, utcnow
from ..ratelimit import limit
from .profile_routes import require_consent

MAX_DEVICES = 10

router = APIRouter(prefix="/v1/me", tags=["notifications"],
                   dependencies=[Depends(limit("me", "rate_limit_default_per_minute"))])


class DeviceIn(BaseModel):
    token: str = Field(min_length=20, max_length=4096, description="The FCM registration token")
    platform: Literal["android", "ios", "web"]


class DeviceOut(BaseModel):
    id: uuid.UUID
    platform: str
    created_at: datetime
    last_seen_at: datetime
    active: bool


class PrefsIn(BaseModel):
    daily_enabled: bool | None = None
    daily_time: time | None = Field(default=None, description="Local time at your city, HH:MM")
    transit_enabled: bool | None = Field(default=None, description="Alerts when a planet changes sign or turns retrograde")


class PrefsOut(BaseModel):
    daily_enabled: bool
    daily_time: time
    transit_enabled: bool
    language: str
    devices: list[DeviceOut]
    # Messages need a birth profile (the card is personal) and at least one active device.
    ready_to_send: bool


def _device_out(d: DeviceToken) -> DeviceOut:
    return DeviceOut(id=d.id, platform=d.platform, created_at=d.created_at, last_seen_at=d.last_seen_at,
                     active=d.disabled_at is None)


def _prefs_out(user: User) -> PrefsOut:
    p = user.notification_prefs
    enabled = p.daily_enabled if p else False
    return PrefsOut(
        daily_enabled=enabled, daily_time=p.daily_time if p else time(7, 30),
        transit_enabled=bool(p and p.transit_enabled), language=user.language,
        devices=[_device_out(d) for d in user.devices],
        ready_to_send=bool((enabled or (p and p.transit_enabled)) and user.profiles and any(d.disabled_at is None for d in user.devices)),
    )


@router.get("/notifications", response_model=PrefsOut)
def get_notifications(user: User = Depends(get_current_user)) -> PrefsOut:
    return _prefs_out(user)


@router.put("/notifications", response_model=PrefsOut)
def set_notifications(body: PrefsIn, user: User = Depends(require_consent),
                      db: Session = Depends(get_db)) -> PrefsOut:
    """Turn the daily message on or off and choose its time. Off until you turn it on."""
    p = user.notification_prefs
    if p is None:
        p = NotificationPrefs(user_id=user.id, daily_enabled=False, daily_time=time(7, 30))
        user.notification_prefs = p
    if body.daily_enabled is not None:
        p.daily_enabled = body.daily_enabled
    if body.transit_enabled is not None:
        p.transit_enabled = body.transit_enabled
    if body.daily_time is not None:
        p.daily_time = body.daily_time.replace(second=0, microsecond=0, tzinfo=None)
    db.commit()
    return _prefs_out(user)


@router.post("/devices", response_model=DeviceOut, status_code=201)
def register_device(body: DeviceIn, user: User = Depends(require_consent),
                    db: Session = Depends(get_db)) -> DeviceOut:
    """Register (or refresh) this device's push token. A token that was on another account moves to this one,
    since a token belongs to the phone, not the person."""
    existing = db.scalar(select(DeviceToken).where(DeviceToken.token == body.token))
    if existing is None and len(user.devices) >= MAX_DEVICES:
        raise HTTPException(status_code=409, detail=f"At most {MAX_DEVICES} devices per account")
    if existing is None:
        existing = DeviceToken(user_id=user.id, token=body.token, platform=body.platform)
        db.add(existing)
    else:
        existing.user_id = user.id
        existing.platform = body.platform
        existing.disabled_at = None
        existing.last_seen_at = utcnow()
    db.commit()
    return _device_out(existing)


@router.delete("/devices/{device_id}", status_code=204)
def remove_device(device_id: uuid.UUID, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)) -> None:
    d = db.get(DeviceToken, device_id)
    if d is None or d.user_id != user.id:  # someone else's device looks the same as a missing one
        raise HTTPException(status_code=404, detail="Device not found")
    db.delete(d)
    db.commit()
