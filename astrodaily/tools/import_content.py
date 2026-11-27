"""Load content snippets from a folder of JSON files into the database.

    python -m astrodaily.tools.import_content <folder> [--version v1] [--check]

Each file is a JSON list of {"signal", "lang", "kind"(optional, "line"), "variant", "text", "status"}.
The whole set is linted first and nothing is written if anything fails. ``--check`` lints and reports
coverage without touching a database. Snippets that disappeared from the folder are marked ``retired``
(not deleted), so a mistaken import can be reversed by importing the old folder again.
"""
import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..content.coverage import coverage_gaps
from ..content.lint import SnippetData, lint_set
from ..db import normalize_database_url
from ..models import ContentSnippet


def read_folder(folder: Path) -> list[SnippetData]:
    out: list[SnippetData] = []
    for path in sorted(folder.glob("**/*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise SystemExit(f"{path}: expected a JSON list")
        for i, row in enumerate(data):
            try:
                out.append(SnippetData(
                    signal=row["signal"], lang=row["lang"], kind=row.get("kind", "line"),
                    variant=row["variant"], text=row["text"], status=row.get("status", "draft")))
            except (KeyError, TypeError) as exc:
                raise SystemExit(f"{path}[{i}]: bad row ({exc!r})")
    return out


def upsert(session: Session, snippets: list[SnippetData], version: str) -> dict[str, int]:
    existing = {(r.signal_key, r.lang, r.kind, r.variant): r for r in session.scalars(select(ContentSnippet))}
    seen, added, updated = set(), 0, 0
    for s in snippets:
        key = (s.signal, s.lang, s.kind, s.variant)
        seen.add(key)
        row = existing.get(key)
        if row is None:
            session.add(ContentSnippet(signal_key=s.signal, lang=s.lang, kind=s.kind, variant=s.variant,
                                       text=s.text, status=s.status, version=version))
            added += 1
        elif (row.text, row.status) != (s.text, s.status):
            row.text, row.status, row.version = s.text, s.status, version
            updated += 1
    retired = 0
    for key, row in existing.items():
        if key not in seen and row.status != "retired":
            row.status = "retired"
            retired += 1
    return {"added": added, "updated": updated, "retired": retired}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", type=Path)
    ap.add_argument("--version", default="dev", help="label stored on changed rows")
    ap.add_argument("--check", action="store_true", help="lint and report coverage only")
    args = ap.parse_args(argv)

    snippets = read_folder(args.folder)
    problems = lint_set(snippets)
    gaps = coverage_gaps(snippets)
    print(f"{len(snippets)} snippets, {len(problems)} lint problems, {len(gaps)} coverage gaps")
    for p in problems:
        print("LINT", p)
    if args.check:
        for key, lang, n in gaps:
            print("GAP ", key, lang, n)
        return 1 if problems else 0
    if problems:
        print("Nothing imported.")
        return 1
    url = get_settings().database_url
    if not url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2
    engine = create_engine(normalize_database_url(url))
    with Session(engine) as session, session.begin():
        print(upsert(session, snippets, args.version))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
