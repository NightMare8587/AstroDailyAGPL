"""What a planet or the Lagna means, for the Chart tab. The wording lives in ``chart_meanings.json`` (see its
``_note``): what each planet stands for, how it works in each sign, and what each house covers. A planet's
"in this sign" and "in this house" lines are put together from those parts, so a reviewer checks about sixty
phrases instead of hundreds of sentences. A hand-written line for a body and sign (``sign_overrides``) wins."""
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ..config import get_settings

_FILE = Path(__file__).with_name("chart_meanings.json")


@dataclass(frozen=True)
class Meaning:
    about: dict[str, str]            # {"en", "hi"}: what it stands for
    in_sign: dict[str, str]
    in_house: dict[str, str] | None  # None for the Lagna (it is the first house itself)
    status: str                      # "draft" or "reviewed": reviewed only when every part used is


@lru_cache(maxsize=1)
def _data() -> dict:
    return json.loads(_FILE.read_text(encoding="utf-8"))


def _status(*groups: str) -> str:
    st = _data()["status"]
    return "reviewed" if all(st[g] == "reviewed" for g in groups) else "draft"


def _allowed(status: str) -> bool:
    return status == "reviewed" or get_settings().chart_meanings_allow_draft


def planet_meaning(key: str, sign: int, sign_name: dict[str, str], house: int) -> Meaning | None:
    d = _data()
    about = d["planets"].get(key)
    if about is None or not (1 <= sign <= 12 and 1 <= house <= 12):
        return None
    role = d["planet_role"][key]
    override = d["sign_overrides"].get(key)
    groups = ["planets", "planet_role", "house_area"] + (["sign_overrides"] if override else ["sign_style"])
    status = _status(*groups)
    if not _allowed(status):
        return None
    if override:
        in_sign = override[sign - 1]
    else:
        style, t = d["sign_style"][sign - 1], d["templates"]["in_sign"]
        in_sign = {lang: t[lang].format(sign=sign_name[lang], role=role[lang], style=style[lang]) for lang in ("en", "hi")}
    area, t = d["house_area"][house - 1], d["templates"]["in_house"]
    in_house = {"en": t["en"].format(n=house, role=role["en"], area=area["en"]),
                "hi": t["hi"].format(ordinal=area["ordinal_hi"], role=role["hi"], area=area["hi"])}
    return Meaning(about=about, in_sign=in_sign, in_house=in_house, status=status)


def lagna_meaning(sign: int) -> Meaning | None:
    d = _data()
    if not 1 <= sign <= 12:
        return None
    status = _status("lagna", "sign_overrides")
    if not _allowed(status):
        return None
    return Meaning(about=d["lagna"], in_sign=d["sign_overrides"]["Lagna"][sign - 1], in_house=None, status=status)
