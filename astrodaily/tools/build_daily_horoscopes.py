"""Write today's horoscope for people who used the app in the last few days, so it is ready when they open it.

    python -m astrodaily.tools.build_daily_horoscopes [--dry-run]

Run it once a day early in the morning (Railway cron, for example 04:00 IST = `30 22 * * *` UTC). Safe to run twice:
days that are already written are skipped. People who were away still get theirs the first time they open the app.
"""
import argparse
import logging
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..api.daily_text_routes import get_daily_llm_client
from ..config import get_settings
from ..db import normalize_database_url
from ..horoscope import prebuild


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="only count who is due; call no model")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    s = get_settings()
    if not s.database_url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2
    client = get_daily_llm_client()
    if client is None and not args.dry_run:
        print("GEMINI_API_KEY is not set", file=sys.stderr)
        return 2
    engine = create_engine(normalize_database_url(s.database_url))
    res = prebuild.run(sessionmaker(engine), client, dry_run=args.dry_run)
    print(res)
    return 1 if res.errors or res.stopped else 0


if __name__ == "__main__":
    raise SystemExit(main())
