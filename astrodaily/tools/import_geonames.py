"""Load GeoNames populated places for one country into the database.

    python -m astrodaily.tools.import_geonames --country IN

Data: GeoNames (https://www.geonames.org), licensed CC BY 4.0. Safe to re-run: the country's rows
are replaced inside one transaction. Downloads go to a temporary folder unless --data-dir already
holds the files (<CC>.zip, alternatenames_<CC>.zip, admin1CodesASCII.txt, admin2Codes.txt).
"""
import argparse
import csv
import io
import sys
import tempfile
import urllib.request
import zipfile
from collections.abc import Iterable, Iterator
from pathlib import Path

from sqlalchemy import create_engine, delete, insert, select
from sqlalchemy.engine import Engine

from ..config import get_settings
from ..db import normalize_database_url
from ..models import Place, PlaceName
from ..places.normalize import normalize

BASE_URL = "https://download.geonames.org/export/dump/"
MAX_NAMES_PER_PLACE = 12
BATCH = 5000


def load_admin_names(lines: Iterable[str], country: str) -> dict[str, str]:
    """admin1CodesASCII.txt / admin2Codes.txt: 'IN.36<TAB>Uttar Pradesh<TAB>...' -> {'IN.36': 'Uttar Pradesh'}."""
    out: dict[str, str] = {}
    prefix = country + "."
    for row in csv.reader(lines, delimiter="\t", quoting=csv.QUOTE_NONE):
        if len(row) >= 2 and row[0].startswith(prefix):
            out[row[0]] = row[1]
    return out


def load_hindi_names(lines: Iterable[str]) -> dict[int, str]:
    """alternateNames: pick the preferred Hindi name per place, else the first one."""
    best: dict[int, tuple[bool, str]] = {}
    for row in csv.reader(lines, delimiter="\t", quoting=csv.QUOTE_NONE):
        if len(row) < 5 or row[2] != "hi" or not row[3] or row[7:8] == ["1"]:  # skip historic
            continue
        try:
            gid = int(row[1])
        except ValueError:
            continue
        preferred = row[4] == "1"
        if gid not in best or (preferred and not best[gid][0]):
            best[gid] = (preferred, row[3])
    return {gid: name for gid, (_, name) in best.items()}


def parse_places(
    lines: Iterable[str], country: str, admin1: dict[str, str], admin2: dict[str, str],
    hindi: dict[int, str],
) -> Iterator[tuple[dict, list[str]]]:
    """Yield (place row, normalised search names) for populated places (feature class P)."""
    for row in csv.reader(lines, delimiter="\t", quoting=csv.QUOTE_NONE):
        if len(row) < 18 or row[6] != "P" or row[8] != country:
            continue
        try:
            gid = int(row[0])
            lat, lon = float(row[4]), float(row[5])
            population = int(row[14] or 0)
        except ValueError:
            continue
        a1 = admin1.get(f"{country}.{row[10]}") if row[10] else None
        a2 = admin2.get(f"{country}.{row[10]}.{row[11]}") if row[10] and row[11] else None
        name_hi = hindi.get(gid)
        place = {
            "id": gid, "name": row[1], "name_hi": name_hi, "state": a1, "district": a2,
            "country_code": country, "latitude": lat, "longitude": lon,
            "population": population, "timezone": row[17] or "UTC",
        }
        raw = [row[1], row[2], *(row[3].split(",") if row[3] else [])]
        if name_hi:
            raw.append(name_hi)
        names: list[str] = []
        for n in raw:
            norm = normalize(n)
            if norm and norm not in names:
                names.append(norm)
            if len(names) >= MAX_NAMES_PER_PLACE:
                break
        yield place, names


def _read_zip_member(path: Path, member: str) -> io.TextIOWrapper:
    zf = zipfile.ZipFile(path)
    return io.TextIOWrapper(zf.open(member), encoding="utf-8", newline="")


def _download(name: str, dest: Path) -> Path:
    target = dest / name.replace("/", "_")
    with urllib.request.urlopen(BASE_URL + name, timeout=120) as r, open(target, "wb") as f:  # noqa: S310
        while chunk := r.read(1 << 20):
            f.write(chunk)
    return target


def import_country(engine: Engine, country: str, data_dir: Path) -> tuple[int, int]:
    """Load files from data_dir into the DB. Returns (places, names) inserted."""
    admin1 = load_admin_names(open(data_dir / "admin1CodesASCII.txt", encoding="utf-8", newline=""), country)
    admin2 = load_admin_names(open(data_dir / "admin2Codes.txt", encoding="utf-8", newline=""), country)
    hindi = load_hindi_names(_read_zip_member(data_dir / f"alternatenames_{country}.zip", f"{country}.txt"))
    places = names = 0
    with engine.begin() as conn:
        old = select(Place.id).where(Place.country_code == country)
        conn.execute(delete(PlaceName).where(PlaceName.place_id.in_(old)))
        conn.execute(delete(Place).where(Place.country_code == country))
        place_batch: list[dict] = []
        name_batch: list[dict] = []

        def flush() -> None:
            if place_batch:
                conn.execute(insert(Place), place_batch)
            if name_batch:
                conn.execute(insert(PlaceName), name_batch)
            place_batch.clear()
            name_batch.clear()

        for place, norms in parse_places(
            _read_zip_member(data_dir / f"{country}.zip", f"{country}.txt"), country, admin1, admin2, hindi
        ):
            place_batch.append(place)
            name_batch.extend({"place_id": place["id"], "name_norm": n} for n in norms)
            places += 1
            names += len(norms)
            if len(place_batch) >= BATCH:
                flush()
        flush()
    return places, names


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--country", default="IN", help="ISO country code (default IN)")
    ap.add_argument("--data-dir", type=Path, help="folder that already holds the GeoNames files")
    ap.add_argument("--database-url", help="override DATABASE_URL")
    args = ap.parse_args(argv)

    url = args.database_url or get_settings().database_url
    if not url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2
    engine = create_engine(normalize_database_url(url), pool_pre_ping=True)
    country = args.country.upper()

    def run(data_dir: Path) -> None:
        p, n = import_country(engine, country, data_dir)
        print(f"Imported {p} places and {n} search names for {country}")

    if args.data_dir:
        run(args.data_dir)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            for name, saved in (
                (f"{country}.zip", f"{country}.zip"),
                (f"alternatenames/{country}.zip", f"alternatenames_{country}.zip"),
                ("admin1CodesASCII.txt", "admin1CodesASCII.txt"),
                ("admin2Codes.txt", "admin2Codes.txt"),
            ):
                print("Downloading", name, file=sys.stderr)
                path = _download(name, d)
                path.rename(d / saved)
            run(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
