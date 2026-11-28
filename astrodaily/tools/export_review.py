"""Write docs/content-review.md: every piece of draft astrology wording in one place, in English and Hindi, for a Jyotish
reviewer to read, correct and approve. Run: python -m astrodaily.tools.export_review"""
import json
from pathlib import Path

from ..calc import matching
from ..content import yoga_text

ROOT = Path(__file__).resolve().parents[2]
MEANINGS = ROOT / "astrodaily" / "content" / "chart_meanings.json"
OUT = ROOT / "docs" / "content-review.md"
SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]


def cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def table(rows: list[tuple[str, str, str]], head: tuple[str, str, str] = ("Item", "English", "Hindi")) -> list[str]:
    out = [f"| {head[0]} | {head[1]} | {head[2]} |", "| --- | --- | --- |"]
    out += [f"| {cell(a)} | {cell(b)} | {cell(c)} |" for a, b, c in rows]
    return out + [""]


def build() -> str:
    d = json.loads(MEANINGS.read_text(encoding="utf-8"))
    L: list[str] = ["# Content for review", "",
                    "Everything below is **draft**: written by a model, not yet checked by a Jyotish reviewer. This file is "
                    "generated (`python -m astrodaily.tools.export_review`); do not edit it. To change a line, edit the source "
                    "named under each heading, and to approve a group set its status to `reviewed`. Wording is shown to people "
                    "only when every part it is built from is reviewed, unless `CHART_MEANINGS_ALLOW_DRAFT` is on (it is on "
                    "while everything is draft).", "",
                    "## What to check", "",
                    "- Is it true to the tradition, and said as a tendency, never as a fate or a guarantee?",
                    "- Is it gentle (nothing frightening about health, loss, marriage or death) and plain (no jargon)?",
                    "- Is the Hindi natural, in Devanagari only, in simple everyday words?",
                    "- Are the rules and tables in the last section right for the school you follow?", ""]
    L += ["## Status", "", "| Group | Status |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in d["status"].items()]
    L += ["", f"Yogas, doshas and strength words: `{yoga_text.STATUS}`.", ""]

    L += ["## What each planet stands for", "", "Source: `chart_meanings.json` → `planets`", ""]
    L += table([(k, v["en"], v["hi"]) for k, v in d["planets"].items()])
    L += ["## Each planet's themes in a few words", "", "Source: `planet_role` (used in the planet-in-sign, planet-in-house and sub-period lines)", ""]
    L += table([(k, v["en"], v["hi"]) for k, v in d["planet_role"].items()])
    L += ["## How a planet works in each sign", "", "Source: `sign_style`; the line reads: " + d["templates"]["in_sign"]["en"], ""]
    L += table([(SIGNS[i], v["en"], v["hi"]) for i, v in enumerate(d["sign_style"])])
    L += ["## What each house covers", "", "Source: `house_area`; the line reads: " + d["templates"]["in_house"]["en"], ""]
    L += table([(f"House {i + 1}", v["en"], v["hi"]) for i, v in enumerate(d["house_area"])])
    L += ["## Hand-written lines for a body in a sign", "", "Source: `sign_overrides` (these win over the sign style)", ""]
    for body, lines in d["sign_overrides"].items():
        L += [f"### {body}", ""] + table([(SIGNS[i], v["en"], v["hi"]) for i, v in enumerate(lines)])
    L += ["## The Lagna", "", "Source: `lagna`", "", f"- English: {d['lagna']['en']}", f"- Hindi: {d['lagna']['hi']}", ""]
    L += ["## What each main period (dasha) is like", "", "Source: `dasha`; a sub-period reads: " + d["templates"]["dasha_sub"]["en"], ""]
    L += table([(k, v["en"], v["hi"]) for k, v in d["dasha"].items()])
    L += ["## Yogas, doshas and Sade Sati", "", "Source: `astrodaily/content/yoga_text.py`. Rules in `astrodaily/calc/yogas.py`: Mangal dosha = "
          "Mars in house 1, 4, 7, 8 or 12 from the Lagna unless Jupiter or Venus aspects or joins it (Brihat Parashara Hora "
          "Shastra 80.47; sources and the other traditions are in `docs/mangal-dosha-sources.md`); Kaal Sarp = all seven planets on one side of Rahu and Ketu; "
          "Gajakesari = Jupiter in house 1, 4, 7 or 10 from the Moon; Budhaditya = Sun and Mercury in one sign; "
          "Chandra-Mangal = Moon and Mars in one sign; the five Mahapurusha yogas = Mars, Mercury, Jupiter, Venus or "
          "Saturn in its own or high sign in house 1, 4, 7 or 10; Sade Sati = Saturn now in the sign before, on, or after "
          "the Moon sign.", ""]
    L += table([(f"{v['name'][0]} / {v['name'][1]}", v["en"], v["hi"]) for v in yoga_text.TEXT.values()])
    L += ["### Planet strength words", ""] + table([(k, v[0], v[1]) for k, v in yoga_text.LEVELS.items()])
    L += ["The strength guide gives points for the sign (exalted +3, own +2, a friend's +1, an enemy's −1, debilitated −3; "
          "the nodes have none), for the house (houses 1, 4, 5, 7, 9, 10 +1; houses 6, 8, 12 −1) and −1 when a planet is "
          "within its combustion distance of the Sun. 3 or more is *strong*, 0 to 2 *steady*, below 0 *tender*. Planets look "
          "at the 7th house from where they stand; Mars also the 4th and 8th, Jupiter the 5th and 9th, Saturn the 3rd and 10th, "
          "Rahu and Ketu the 5th and 9th.", ""]
    L += ["## Compatibility (Ashtakoota)", "", "Source: `astrodaily/calc/matching.py` and `docs/compatibility.md`. Points: Varna 1, "
          "Vashya 2, Tara 3, Yoni 4, Graha Maitri 5, Gana 6, Bhakoot 7, Nadi 8. The first person is the first column of the "
          "tables. Where books differ (Varna of the earth and air signs, the Vashya table and the Sagittarius and Capricorn "
          "halves, Tara, Gana for the first and second person) please say which you follow.", ""]
    L += ["### Varna by Moon sign", ""] + table([(SIGNS[i], matching.VARNA_NAME[matching.VARNA_OF_SIGN[i + 1]], "") for i in range(12)], ("Sign", "Varna", ""))
    L += ["### Gana by birth star", ""] + table([(str(i + 1), g, "") for i, g in enumerate(matching.GANA_OF_NAKSHATRA)], ("Star number", "Gana", ""))
    L += ["### Gana points (first person, second person)", ""] + table([(f"{a} / {b}", str(v), "") for (a, b), v in matching._GANA.items()], ("Pair", "Points", ""))
    L += ["### Vashya points (first person's group down, second person's across)", "",
          "| | " + " | ".join(matching.VASHYA_GROUPS) + " |", "| --- | " + " | ".join("---" for _ in matching.VASHYA_GROUPS) + " |"]
    L += [f"| {g} | " + " | ".join(f"{v:g}" for v in row) + " |" for g, row in zip(matching.VASHYA_GROUPS, matching._VASHYA)] + [""]
    L += ["### Yoni animal by birth star", ""] + table([(str(i + 1), a, "") for i, a in enumerate(matching.YONI_OF_NAKSHATRA)], ("Star number", "Animal", ""))
    L += ["### Nadi by birth star", ""] + table([(str(i + 1), a, "") for i, a in enumerate(matching.NADI_OF_NAKSHATRA)], ("Star number", "Nadi", ""))
    L += ["## Daily horoscope, love reading, planet cards and match summary", "",
          "These are written by the model from computed facts, so there is no fixed wording to review. The instructions the "
          "model follows are in `astrodaily/chat/prompt.py` (`DAILY_SYSTEM`, `LOVE_SYSTEM`, `PLANET_CARDS_SYSTEM`, "
          "`MATCH_SYSTEM`): please read them, and the planet chosen for each life area (career Saturn, money Jupiter, "
          "relationships Venus, health and energy Mars, mind Mercury).", ""]
    return "\n".join(L)


def main() -> None:
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
