"""Write today's horoscope ahead of time for people who used the app recently, so it is ready when they open it.
People who were away still get theirs on demand (``daily_text.get_or_build``). Safe to run twice: a day that is
already written is skipped."""
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from ..chat.context import day_location
from ..chat.llm import LlmClient, LlmError
from ..config import get_settings
from ..models import RefreshToken, User, primary_profile
from . import daily_text, service

log = logging.getLogger("astrodaily.horoscope")


@dataclass
class Result:
    due: int = 0        # people with a day to write
    built: int = 0
    skipped: int = 0    # already written, or over the free limit
    errors: int = 0
    stopped: bool = False  # too many failures: the rest were left for on-demand


def active_user_ids(db: Session, now: datetime, days: int) -> list:
    """People whose app signed in or refreshed its session recently (a session refreshes about every 15 minutes
    while the app is in use)."""
    since = now - timedelta(days=days)
    return list(db.scalars(
        select(RefreshToken.user_id).group_by(RefreshToken.user_id).having(func.max(RefreshToken.created_at) >= since)))


def _work(db: Session, now: datetime, days: int) -> list[tuple]:
    items = []
    for uid in active_user_ids(db, now, days):
        user = db.get(User, uid)
        if user is None or user.consented_at is None:
            continue
        profile = primary_profile(user)
        if profile is None:
            continue
        day = service.today_in(day_location(user, profile).timezone)
        lang = "hi" if user.language == "hi" else "en"
        if daily_text.saved(db, profile, day, lang) is None:
            items.append((user.id, profile.id, day, lang))
    return items


def run(session_factory: sessionmaker, client: LlmClient | None, now: datetime | None = None,
        dry_run: bool = False) -> Result:
    s = get_settings()
    now = now or datetime.now(timezone.utc)
    res = Result()
    with session_factory() as db:
        items = _work(db, now, s.daily_horoscope_active_days)
    res.due = len(items)
    if dry_run or not items:
        return res

    failures = [0]
    lock = threading.Lock()

    def failed() -> str:
        with lock:
            failures[0] += 1
        return "error"

    def one(item) -> str:
        with lock:
            if failures[0] >= s.daily_horoscope_build_max_errors:
                return "stopped"  # an outage or a spent quota: leave the rest for on-demand
        uid, pid, day, lang = item
        with session_factory() as db:
            user = db.get(User, uid)
            profile = next((p for p in user.profiles if p.id == pid), None) if user else None
            if profile is None:
                return "skipped"
            try:
                daily_text.get_or_build(db, user, profile, day, lang, client)
                return "built"
            except daily_text.FreeLimitReached:
                return "skipped"
            except LlmError:
                return failed()
            except Exception:  # one person's failure must not end the run
                log.exception("daily horoscope build failed")
                return failed()

    workers = max(1, s.daily_horoscope_build_workers)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for outcome in pool.map(one, items):
            if outcome == "built":
                res.built += 1
            elif outcome == "skipped":
                res.skipped += 1
            elif outcome == "error":
                res.errors += 1
            else:
                res.stopped = True
    return res
