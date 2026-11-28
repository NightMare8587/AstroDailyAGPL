"""One delivery run: find users whose daily message is due now, send it, record that it was sent."""
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..content.apply import localize
from ..content.catalog import Catalog
from ..horoscope import service
from ..models import BirthProfile, NotificationLog, NotificationPrefs, User, primary_profile, utcnow
from .message import daily_push
from .sender import Sender

log = logging.getLogger("astrodaily.notify")
KIND = "daily"
MAX_ATTEMPTS = 3


@dataclass
class RunResult:
    considered: int = 0
    sent: int = 0
    failed: int = 0
    skipped: int = 0
    devices_disabled: int = 0
    sender: str = ""
    errors: list[str] = field(default_factory=list)


def user_location(user: User, profile: BirthProfile) -> service.DayLocation:
    """Where the user is: their home city, else where they were born (same rule as the card API)."""
    p = user.home_place
    if p is not None:
        return service.DayLocation(p.latitude, p.longitude, p.timezone, p.name, "home")
    return service.DayLocation(profile.latitude, profile.longitude, profile.timezone, profile.place_name, "profile")


def due_local_date(user: User, prefs: NotificationPrefs, profile: BirthProfile, now: datetime,
                   max_late: timedelta) -> date | None:
    """The user's local date if their send time has passed within the allowed lateness, else None."""
    tz = ZoneInfo(user_location(user, profile).timezone)
    local_now = now.astimezone(tz)
    target = datetime.combine(local_now.date(), prefs.daily_time, tzinfo=tz)
    return local_now.date() if timedelta(0) <= local_now - target <= max_late else None


def _claim(db: Session, user: User, day: date) -> bool:
    """Take the right to send this user's message for this day. False if someone else already has it."""
    row = db.scalar(select(NotificationLog).where(
        NotificationLog.user_id == user.id, NotificationLog.kind == KIND, NotificationLog.local_date == day))
    if row is None:
        try:
            with db.begin_nested():
                db.add(NotificationLog(user_id=user.id, kind=KIND, local_date=day, status="sending", attempts=1))
            return True
        except IntegrityError:
            return False
    if row.status == "failed" and row.attempts < MAX_ATTEMPTS:
        res = db.execute(update(NotificationLog).where(
            NotificationLog.id == row.id, NotificationLog.status == "failed", NotificationLog.attempts == row.attempts,
        ).values(status="sending", attempts=row.attempts + 1, updated_at=utcnow()))
        return res.rowcount == 1
    return False


def run_once(db: Session, sender: Sender, catalog: Catalog, now: datetime | None = None,
             max_late_minutes: int = 180, dry_run: bool = False) -> RunResult:
    """dry_run: work out and count what would be sent, writing nothing and sending nothing."""
    now = now or datetime.now(timezone.utc)
    out = RunResult(sender=sender.name)
    users = db.scalars(
        select(User).join(NotificationPrefs, NotificationPrefs.user_id == User.id)
        .where(NotificationPrefs.daily_enabled.is_(True), User.consented_at.is_not(None))
    ).all()
    for user in users:
        out.considered += 1
        profile = primary_profile(user)
        devices = [d for d in user.devices if d.disabled_at is None]
        prefs = user.notification_prefs
        if profile is None or not devices or prefs is None:
            out.skipped += 1
            continue
        day = due_local_date(user, prefs, profile, now, timedelta(minutes=max_late_minutes))
        if day is None:
            out.skipped += 1
            continue
        if dry_run:
            if db.scalar(select(NotificationLog.id).where(
                    NotificationLog.user_id == user.id, NotificationLog.kind == KIND,
                    NotificationLog.local_date == day)) is not None:
                out.skipped += 1
            else:
                out.sent += 1
            continue
        if not _claim(db, user, day):
            out.skipped += 1
            continue
        db.commit()  # the claim is durable before anything is sent
        try:
            loc = user_location(user, profile)
            core = service.personal_card_core(profile, day, loc.latitude, loc.longitude, loc.timezone)
            card, _ = localize(service.with_location(core, loc), catalog, user.language,
                               f"profile:{profile.id}:{day}")
            push = daily_push(card, user.language)
            outcomes = []
            for d in devices:
                oc = sender.send(d.token, push)
                outcomes.append(oc)
                if oc == "dead_token":
                    d.disabled_at = utcnow()
                    out.devices_disabled += 1
            ok = "ok" in outcomes
        except Exception as exc:  # one bad user must not stop the run
            ok = False
            out.errors.append(type(exc).__name__)
            log.exception("daily notification failed")
        row = db.scalar(select(NotificationLog).where(
            NotificationLog.user_id == user.id, NotificationLog.kind == KIND, NotificationLog.local_date == day))
        row.status = "sent" if ok else "failed"
        db.commit()
        out.sent += ok
        out.failed += not ok
    return out
