import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from astrodaily.calc.kundli import compute_chart, resolve_birth_moment
from astrodaily.config import get_settings
from astrodaily.content import catalog as cat
from astrodaily.content.apply import localize
from astrodaily.content.coverage import coverage_gaps
from astrodaily.content.keys import REQUIRED_KEYS, SLOTS, key_for
from astrodaily.content.lint import SnippetData, lint_set, lint_snippet
from astrodaily.content.render import fill, slot_values
from astrodaily.horoscope import NatalContext, build_day_report, natal_from_chart
from astrodaily.models import ContentSnippet
from astrodaily.tools.import_content import main as import_main, read_folder, upsert

SAMPLES = Path(__file__).resolve().parent.parent / "content-samples"


def snip(**over):
    base = dict(signal="amavasya", lang="en", kind="line", variant=1,
                text="A quiet day for rest and reflection.", status="draft")
    base.update(over)
    return SnippetData(**base)


# ------------------------------------------------------------------ lint

def test_clean_snippet_passes():
    assert lint_snippet(snip()) == []


@pytest.mark.parametrize("over,needle", [
    ({"text": "You may face death today."}, "banned"),
    ({"text": "This will definitely work out."}, "banned"),
    ({"text": "An ancient rule says rest."}, "banned"),
    ({"lang": "hi", "text": "आज बीमारी का डर रहेगा।"}, "banned"),
    ({"text": "Short"}, "shorter"),
    ({"text": "x" * 161}, "longer"),
    ({"text": "A quiet {nonsense} day for rest."}, "unknown slot"),
    ({"text": "A quiet {yoga} day for rest."}, "not available"),
    ({"text": "A quiet {day for rest."}, "malformed"),
    ({"signal": "not_a_signal"}, "unknown signal"),
    ({"lang": "fr"}, "lang"),
    ({"status": "approved"}, "status"),
    ({"variant": 0}, "variant"),
    ({"text": " leading space here ok"}, "whitespace"),
    ({"lang": "hi", "text": "A quiet day for rest."}, "Devanagari"),
    ({"text": "शांत दिन विश्राम के लिए है।"}, "Devanagari"),
    ({"lang": "hi", "text": "शांत दिन rest के लिए है।"}, "Latin"),
])
def test_lint_catches(over, needle):
    errs = lint_snippet(snip(**over))
    assert any(needle in e for e in errs), errs


def test_set_lint_catches_duplicates():
    a, b = snip(), snip(signal="rikta_tithi", text="A quiet day for rest and reflection.")
    errs = lint_set([a, snip(variant=1, text="A different quiet day for rest."), b])
    assert any("duplicate variant" in e for e in errs)
    assert any("same text" in e for e in errs)


def test_sample_library_is_clean_and_complete():
    snippets = read_folder(SAMPLES)
    assert lint_set(snippets) == []
    assert coverage_gaps(snippets) == []
    assert {s.status for s in snippets} == {"draft"}  # nothing is reviewed until a person says so


def test_coverage_reports_gaps():
    gaps = coverage_gaps([snip()])
    assert ("amavasya", "hi", 0) in gaps and ("amavasya", "en", 0) not in gaps
    assert coverage_gaps([snip(status="retired")]) and ("amavasya", "en", 0) in coverage_gaps([snip(status="retired")])


# ------------------------------------------------------------------ keys vs the real engine

def _real_signals():
    """Signals across ~15 months for several Moon signs and three real birth charts (Level A and B)."""
    out = []
    start = date(2025, 1, 1)
    for i in range(0, 460, 5):
        day = start + timedelta(i)
        for rashi in (1, 4, 8, 11):
            rep = build_day_report(day, 28.6139, 77.2090, "Asia/Kolkata", NatalContext(moon_sign=rashi))
            out += rep.signals + ([rep.coming_up] if rep.coming_up else [])
    for bd in (date(1990, 5, 17), date(1985, 11, 2), date(2001, 3, 9)):
        birth = resolve_birth_moment(bd, time(10, 30), "Asia/Kolkata", None)
        for i in range(0, 460, 9):
            day = start + timedelta(i)
            noon = datetime.combine(day, time(12, 0), tzinfo=timezone.utc)
            natal = natal_from_chart(compute_chart(birth, 28.6, 77.2, "mean", noon), as_of=noon)
            rep = build_day_report(day, 28.6139, 77.2090, "Asia/Kolkata", natal)
            out += rep.signals
    return out


@pytest.fixture(scope="module")
def real_signals():
    return _real_signals()


def test_every_engine_signal_has_a_content_key(real_signals):
    ids = {s.id for s in real_signals}
    assert len(ids) > 60
    unknown = {i for i in ids if key_for(i) not in SLOTS}
    assert not unknown, f"engine emits signals the content library does not know: {unknown}"


def test_sample_library_fills_every_real_signal_in_both_languages(real_signals):
    snippets = read_folder(SAMPLES)
    c = cat.Catalog([(s.signal, s.lang, s.variant, s.text, s.status, "t") for s in snippets])
    for sig in real_signals:
        params = sig.params
        for lang in ("en", "hi"):
            line = c.pick(sig.id, params, lang, "seed")
            assert line is not None, f"{sig.id}/{lang} could not be filled from {params}"
            assert "{" not in line.text


def test_slots_declared_per_key_are_resolvable(real_signals):
    for sig in real_signals:
        have = set(slot_values(sig.params, "en"))
        need = SLOTS[key_for(sig.id)]
        assert need <= have, f"{sig.id}: slots {need - have} cannot be resolved from params {sorted(sig.params)}"


# ------------------------------------------------------------------ render and catalog

def test_fill_uses_language_and_declines_missing_slots():
    p = {"nakshatra": 4}
    assert fill("{nakshatra} is steady", p, "en") == "Rohini is steady"
    assert fill("{nakshatra} स्थिर है", p, "hi") == "रोहिणी स्थिर है"
    assert fill("{yoga} yoga", p, "en") is None


def test_pick_is_deterministic_and_rotates():
    rows = [("amavasya", "en", v, f"Variant {v} of a quiet new moon day", "reviewed", "t") for v in (1, 2, 3, 4)]
    c = cat.Catalog(rows)
    assert c.pick("amavasya", {}, "en", "s1").text == c.pick("amavasya", {}, "en", "s1").text
    seen = {c.pick("amavasya", {}, "en", f"user:{i}").text for i in range(40)}
    assert len(seen) == 4


def test_pick_skips_variant_it_cannot_fill():
    rows = [("inauspicious_yoga", "en", 1, "{yoga} is in force today", "reviewed", "t"),
            ("inauspicious_yoga", "en", 2, "Double-check details today", "reviewed", "t")]
    c = cat.Catalog(rows)
    for i in range(10):
        assert c.pick("inauspicious_yoga", {}, "en", f"s{i}").text == "Double-check details today"


def test_dasha_ids_share_one_key():
    assert key_for("dasha_moon_saturn") == key_for("dasha_venus_sun") == "dasha"


def test_localize_falls_back_and_flags():
    card = {"dos": [{"id": "amavasya", "params": {}, "reason": "r"}], "donts": [], "why": [],
            "theme": None, "coming_up": None}
    c = cat.Catalog([("amavasya", "en", 1, "A quiet day for rest and reflection.", "reviewed", "t")])
    out, in_hi = localize(card, c, "hi", "s")
    assert out["dos"][0]["text"] == "A quiet day for rest and reflection." and out["dos"][0]["text_lang"] == "en"
    assert in_hi is False
    out, in_en = localize(card, c, "en", "s")
    assert in_en is True
    out, none = localize(card, cat.EMPTY, "en", "s")
    assert out["dos"][0]["text"] is None and none is False
    assert "text" not in card["dos"][0]  # the cached core is never mutated


# ------------------------------------------------------------------ importer and database

def test_importer_upserts_and_retires(engine, tmp_path):
    from sqlalchemy.orm import Session
    folder = tmp_path / "c"
    folder.mkdir()

    def write(rows):
        (folder / "a.json").write_text(json.dumps(rows), encoding="utf-8")

    a = {"signal": "amavasya", "lang": "en", "variant": 1, "text": "A quiet day for rest and reflection."}
    b = {"signal": "amavasya", "lang": "en", "variant": 2, "text": "A still new moon, good for slowing down."}
    write([a, b])
    with Session(engine) as s, s.begin():
        assert upsert(s, read_folder(folder), "v1") == {"added": 2, "updated": 0, "retired": 0}
    write([{**a, "text": "A quiet new moon day for rest and reflection.", "status": "reviewed"}])
    with Session(engine) as s, s.begin():
        assert upsert(s, read_folder(folder), "v2") == {"added": 0, "updated": 1, "retired": 1}
    with Session(engine) as s:
        rows = {r.variant: r for r in s.scalars(select(ContentSnippet))}
    assert rows[1].status == "reviewed" and rows[1].version == "v2"
    assert rows[2].status == "retired"


def test_import_main_refuses_when_lint_fails(tmp_path, capsys):
    (tmp_path / "bad.json").write_text(json.dumps(
        [{"signal": "amavasya", "lang": "en", "variant": 1, "text": "You may face death."}]), encoding="utf-8")
    assert import_main([str(tmp_path)]) == 1
    assert "Nothing imported" in capsys.readouterr().out
    assert import_main([str(tmp_path), "--check"]) == 1


def test_check_mode_passes_on_the_samples(capsys):
    assert import_main([str(SAMPLES), "--check"]) == 0
    assert "0 lint problems, 0 coverage gaps" in capsys.readouterr().out


# ------------------------------------------------------------------ API

def _load(client, status="reviewed", only=None):
    with client.session_factory() as db:
        for s in read_folder(SAMPLES):
            if only and s.signal not in only:
                continue
            db.add(ContentSnippet(signal_key=s.signal, lang=s.lang, kind=s.kind, variant=s.variant,
                                  text=s.text, status=status, version="t"))
        db.commit()
    cat.reset()


def test_api_without_content_keeps_engine_wording(client):
    r = client.get("/v1/horoscope/rashi/5?date=2025-11-05").json()
    assert all(s["text"] is None for s in r["dos"] + r["donts"])
    assert r["translated"] is False and r["text_language"] == "en" and r["dos"][0]["reason"]


def test_api_serves_reviewed_content_in_hindi(client):
    _load(client, "reviewed")
    r = client.get("/v1/horoscope/rashi/5?date=2025-11-05&lang=hi").json()
    lines = r["dos"] + r["donts"]
    assert r["translated"] is True and r["text_language"] == "hi"
    assert all(s["text_lang"] == "hi" and "{" not in s["text"] for s in lines)
    assert any("ऀ" <= ch <= "ॿ" for ch in lines[0]["text"])
    assert lines[0]["reason"]  # the engine's reason is still there
    en = client.get("/v1/horoscope/rashi/5?date=2025-11-05&lang=en").json()
    assert en["translated"] is True and all(s["text_lang"] == "en" for s in en["dos"])
    again = client.get("/v1/horoscope/rashi/5?date=2025-11-05&lang=hi").json()
    assert [s["text"] for s in again["dos"]] == [s["text"] for s in r["dos"]]  # stable


def test_api_hides_drafts_unless_allowed(client, monkeypatch):
    _load(client, "draft")
    r = client.get("/v1/horoscope/rashi/5?date=2025-11-05").json()
    assert all(s["text"] is None for s in r["dos"] + r["donts"])
    monkeypatch.setenv("CONTENT_ALLOW_DRAFT", "true")
    get_settings.cache_clear()
    try:
        cat.reset()
        r = client.get("/v1/horoscope/rashi/5?date=2025-11-05").json()
        assert all(s["text"] for s in r["dos"] + r["donts"])
    finally:
        monkeypatch.delenv("CONTENT_ALLOW_DRAFT")
        get_settings.cache_clear()
        cat.reset()


def test_api_partial_hindi_falls_back_to_english_per_line(client):
    # Only English exists for some keys: the card must say it is not fully translated.
    with client.session_factory() as db:
        for s in read_folder(SAMPLES):
            if s.lang == "en":
                db.add(ContentSnippet(signal_key=s.signal, lang="en", kind="line", variant=s.variant,
                                      text=s.text, status="reviewed", version="t"))
        db.commit()
    cat.reset()
    r = client.get("/v1/horoscope/rashi/5?date=2025-11-05&lang=hi").json()
    assert r["translated"] is False and r["text_language"] == "en"
    assert all(s["text_lang"] == "en" for s in r["dos"] + r["donts"])
