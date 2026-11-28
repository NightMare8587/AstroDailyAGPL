"""Planet change alerts: a planet moves into a new sign, or turns retrograde or direct.

The events are the same for everyone; only the house (counted from the person's Moon sign) is personal. A user who
turned the alerts on is told on the morning of the event's local day, once per event.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..calc import zodiac
from ..calc.transits import STATION_PLANETS, house_from, next_ingress, next_station, sign_at
from ..models import NotificationLog, NotificationPrefs, User, primary_profile, utcnow
from .dispatch import RunResult, claim, user_location
from .sender import Push, Sender

log = logging.getLogger("astrodaily.notify")

SEND_AT = time(9, 0)  # local time of the morning message
INGRESS_PLANETS = ("Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu")  # Ketu always moves with Rahu
LOOK_BACK = timedelta(hours=26)  # events from yesterday can still be due for people far to the west
LOOK_AHEAD = timedelta(hours=38)  # and tomorrow's for people far to the east


@dataclass(frozen=True)
class Event:
    kind: str            # "in" (enters a sign), "rx" (turns retrograde), "dr" (turns direct); also the log's tag
    planet: str
    when: datetime       # UTC
    sign: int            # the sign it is in after the event

    @property
    def log_kind(self) -> str:  # NotificationLog.kind is 16 characters at most
        return f"tr:{self.planet[:3]}:{self.kind}"


def events_between(start: datetime, end: datetime) -> list[Event]:
    """Every sign change and station of the tracked planets from ``start`` to ``end``, oldest first."""
    out: list[Event] = []
    for planet in INGRESS_PLANETS:
        after = start
        while after < end:
            ing = next_ingress(planet, after, (end - after).total_seconds() / 86400)
            if ing is None or ing.when > end:
                break
            out.append(Event("in", planet, ing.when, ing.to_sign))
            after = ing.when + timedelta(seconds=1)
    for planet in STATION_PLANETS:
        st = next_station(planet, start, (end - start).total_seconds() / 86400)
        if st is not None and st.when <= end:
            out.append(Event("rx" if st.retrograde else "dr", planet, st.when, sign_at(planet, st.when)))
    return sorted(out, key=lambda e: e.when)


ORDINAL_EN = {1: "1st", 2: "2nd", 3: "3rd"}
ORDINAL_HI = {1: "पहले", 2: "दूसरे", 3: "तीसरे", 4: "चौथे", 5: "पाँचवें", 6: "छठे", 7: "सातवें", 8: "आठवें",
              9: "नौवें", 10: "दसवें", 11: "ग्यारहवें", 12: "बारहवें"}

TITLE = {
    "in": ("{planet} changes sign today", "{planet} आज राशि बदलता है"),
    "rx": ("{planet} turns retrograde today", "{planet} आज वक्री होता है"),
    "dr": ("{planet} turns direct today", "{planet} आज मार्गी होता है"),
}


def transit_push(event: Event, moon_sign: int, lang: str) -> Push:
    """The lock screen is public: planet, sign and house only, nothing about the person."""
    i = 0 if lang == "en" else 1
    planet = zodiac.PLANET_NAMES[event.planet][i]
    sign = zodiac.SIGNS[event.sign - 1][i]
    house = house_from(event.sign, moon_sign)
    title = TITLE[event.kind][i].format(planet=planet)
    if lang == "en":
        n = ORDINAL_EN.get(house, f"{house}th")
        verb = "enters" if event.kind == "in" else "is in"
        extra = f" Ketu moves to {zodiac.SIGNS[(event.sign + 5) % 12][0]}." if event.planet == "Rahu" else ""
        body = f"{planet} {verb} {sign}, your {n} house from your Moon sign.{extra}"
    else:
        verb = "में प्रवेश करता है" if event.kind == "in" else "में है"
        extra = f" केतु {zodiac.SIGNS[(event.sign + 5) % 12][1]} में जाता है।" if event.planet == "Rahu" else ""
        body = f"{planet} {sign} {verb}, आपकी चंद्र राशि से {ORDINAL_HI[house]} भाव में।{extra}"
    return Push(title=title, body=body, data={"type": "transit", "planet": event.planet, "event": event.kind})


def run_transit_once(db: Session, sender: Sender, now: datetime | None = None, max_late_minutes: int = 180,
                     dry_run: bool = False) -> RunResult:
    now = now or datetime.now(timezone.utc)
    out = RunResult(sender=sender.name)
    events = events_between(now - LOOK_BACK, now + LOOK_AHEAD)
    users = db.scalars(
        select(User).join(NotificationPrefs, NotificationPrefs.user_id == User.id)
        .where(NotificationPrefs.transit_enabled.is_(True), User.consented_at.is_not(None))
    ).all()
    from ..api.profile_routes import profile_moon  # the one place that works out a Moon sign for a profile
    for user in users:
        out.considered += 1
        profile = primary_profile(user)
        devices = [d for d in user.devices if d.disabled_at is None]
        if profile is None or not devices:
            out.skipped += 1
            continue
        tz = ZoneInfo(user_location(user, profile).timezone)
        local_now = now.astimezone(tz)
        moon_sign = profile_moon(profile)[0]
        if moon_sign is None:
            out.skipped += 1
            continue
        for event in events:
            day = event.when.astimezone(tz).date()
            due = datetime.combine(day, SEND_AT, tzinfo=tz)
            if not timedelta(0) <= local_now - due <= timedelta(minutes=max_late_minutes):
                continue
            if dry_run:
                already = db.scalar(select(NotificationLog.id).where(
                    NotificationLog.user_id == user.id, NotificationLog.kind == event.log_kind,
                    NotificationLog.local_date == day))
                out.sent += already is None
                out.skipped += already is not None
                continue
            if not claim(db, user, day, event.log_kind):
                out.skipped += 1
                continue
            db.commit()  # the claim is durable before anything is sent
            ok = False
            try:
                push = transit_push(event, moon_sign, user.language)
                outcomes = []
                for d in devices:
                    oc = sender.send(d.token, push)
                    outcomes.append(oc)
                    if oc == "dead_token":
                        d.disabled_at = utcnow()
                        out.devices_disabled += 1
                ok = "ok" in outcomes
            except Exception as exc:  # one bad user must not stop the run
                out.errors.append(type(exc).__name__)
                log.exception("transit notification failed")
            row = db.scalar(select(NotificationLog).where(
                NotificationLog.user_id == user.id, NotificationLog.kind == event.log_kind,
                NotificationLog.local_date == day))
            row.status = "sent" if ok else "failed"
            db.commit()
            out.sent += ok
            out.failed += not ok
    return out
