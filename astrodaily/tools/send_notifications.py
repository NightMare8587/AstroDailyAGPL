"""Send the daily push messages that are due now.

    python -m astrodaily.tools.send_notifications [--dry-run]

Run it every 5 to 10 minutes (Railway cron). Safe to run twice at once or to re-run: each user is claimed per
local day before sending. Without FCM_SERVICE_ACCOUNT_JSON it only logs what it would do.
"""
import argparse
import logging
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from ..config import get_settings
from ..content.catalog import load_catalog
from ..db import normalize_database_url
from ..notify.dispatch import run_once
from ..notify.sender import LogSender, make_sender


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="claim and build messages but send nothing")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    s = get_settings()
    if not s.database_url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2
    sender = LogSender() if args.dry_run else make_sender(s.fcm_service_account_json)  # dry-run never sends
    engine = create_engine(normalize_database_url(s.database_url))
    with Session(engine) as db:
        res = run_once(db, sender, load_catalog(db), max_late_minutes=s.notify_max_late_minutes, dry_run=args.dry_run)
    print(res)
    return 1 if res.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
