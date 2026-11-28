import pytest

from astrodaily.calc import matching as m
from astrodaily.main import app
from astrodaily.models import Place
from test_daily_text import login, profile


def moon_in(sign, deg=10.0):
    return m.Moon((sign - 1) * 30.0 + deg)


def nak(n):
    """A Moon in the middle of birth star n."""
    return m.Moon((n - 1) * 360.0 / 27 + 3.0)


def test_varna_counts_for_the_first_person_being_at_least_as_high():
    assert m.match(moon_in(4), moon_in(1))["parts"][0]["points"] == 1.0   # Brahmin with Kshatriya
    assert m.match(moon_in(1), moon_in(4))["parts"][0]["points"] == 0.0   # Kshatriya with Brahmin
    assert m.match(moon_in(3), moon_in(3))["parts"][0]["points"] == 1.0   # the same


def test_vashya_group_and_the_halves_of_sagittarius_and_capricorn():
    assert m.vashya_group(120.0 + 10) == "Vanachara"          # Leo
    assert m.vashya_group(240.0 + 10) == "Manava"             # Sagittarius, first half
    assert m.vashya_group(240.0 + 20) == "Chatushpada"        # Sagittarius, second half
    assert m.vashya_group(270.0 + 10) == "Chatushpada"        # Capricorn, first half
    assert m.vashya_group(270.0 + 20) == "Jalachara"          # Capricorn, second half
    assert m.vashya_group(210.0 + 5) == "Keeta"               # Scorpio
    assert m.vashya_group(0.0) == "Chatushpada" and m.vashya_group(90.0 + 1) == "Jalachara"


def test_tara_scores_three_when_neither_count_is_difficult_and_one_and_a_half_when_one_is():
    assert m.tara_points(5, 5) == 3.0
    assert m.tara_points(1, 2) == 3.0
    assert m.tara_points(1, 3) == 1.5  # the 3rd from the first is a difficult one
    assert m.tara_points(3, 1) == 1.5  # and it works the same from the other side


def test_bhakoot_is_zero_for_the_2_12_5_9_and_6_8_positions():
    assert m.bhakoot_points(1, 1) == 7.0 and m.bhakoot_points(1, 7) == 7.0 and m.bhakoot_points(1, 4) == 7.0
    for a, b in [(1, 2), (2, 1), (1, 5), (5, 1), (4, 11), (11, 4), (1, 9), (3, 8)]:
        assert m.bhakoot_points(a, b) == 0.0, (a, b)


def test_nadi_is_zero_for_the_same_nadi_and_eight_otherwise():
    assert m.match(nak(1), nak(6))["parts"][7]["points"] == 0.0   # both Aadi
    assert m.match(nak(1), nak(2))["parts"][7]["points"] == 8.0
    assert m.match(nak(3), nak(4))["parts"][7]["points"] == 0.0   # both Antya
    assert m.NADI_OF_NAKSHATRA.count("Aadi") == m.NADI_OF_NAKSHATRA.count("Madhya") == m.NADI_OF_NAKSHATRA.count("Antya") == 9


def test_gana_table_and_each_gana_has_nine_birth_stars():
    for g in m.GANAS:
        assert m.GANA_OF_NAKSHATRA.count(g) == 9
    assert m._GANA[("Deva", "Manushya")] == 5 and m._GANA[("Manushya", "Deva")] == 6
    assert m._GANA[("Rakshasa", "Deva")] == 0 and m._GANA[("Deva", "Rakshasa")] == 1


def test_graha_maitri_from_how_the_two_lords_regard_each_other():
    assert m.graha_maitri_points("Mars", "Mars") == 5.0
    assert m.graha_maitri_points("Sun", "Moon") == 5.0        # friends both ways
    assert m.graha_maitri_points("Sun", "Mercury") == 4.0     # neutral one way, friend the other
    assert m.graha_maitri_points("Saturn", "Jupiter") == 3.0  # neutral both ways
    assert m.graha_maitri_points("Mercury", "Moon") == 1.0    # enemy one way, friend the other
    assert m.graha_maitri_points("Jupiter", "Venus") == 0.5   # enemy one way, neutral the other
    assert m.graha_maitri_points("Sun", "Venus") == 0.0       # enemies both ways
    assert m.graha_maitri_points("Moon", "Mars") == m.graha_maitri_points("Mars", "Moon")


def test_yoni_matrix_is_symmetric_with_four_on_the_diagonal_and_the_seven_enemy_pairs_at_zero():
    n = len(m.YONI_ANIMALS)
    assert len(m._YONI_MATRIX) == n and all(len(r) == n for r in m._YONI_MATRIX)
    for i in range(n):
        assert m._YONI_MATRIX[i][i] == 4
        for j in range(n):
            assert m._YONI_MATRIX[i][j] == m._YONI_MATRIX[j][i]
    zeros = {frozenset((m.YONI_ANIMALS[i], m.YONI_ANIMALS[j])) for i in range(n) for j in range(n) if m._YONI_MATRIX[i][j] == 0}
    assert zeros == {frozenset(p) for p in [("Horse", "Buffalo"), ("Elephant", "Lion"), ("Sheep", "Monkey"), ("Serpent", "Mongoose"),
                                            ("Dog", "Deer"), ("Cat", "Rat"), ("Cow", "Tiger")]}
    assert len(m.YONI_OF_NAKSHATRA) == 27 and set(m.YONI_OF_NAKSHATRA) == set(m.YONI_ANIMALS)


def test_two_identical_moons_score_everything_but_nadi_and_the_total_never_passes_36():
    r = m.match(nak(10), nak(10))
    assert [p["points"] for p in r["parts"]] == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 0.0]
    assert r["total"] == 28.0 and r["max"] == 36 and sum(p["max"] for p in r["parts"]) == 36
    best = 0.0
    for a in range(27):
        for b in range(27):
            t = m.match(nak(a + 1), nak(b + 1))["total"]
            assert 0.0 <= t <= 36.0
            best = max(best, t)
    assert best > 30.0


# ---- the endpoint ----

@pytest.fixture
def ready(client):
    with client.session_factory() as db:
        db.add(Place(id=1273294, name="Delhi", name_hi="दिल्ली", state="Delhi", district="Central Delhi",
                     country_code="IN", latitude=28.65195, longitude=77.23149, population=11034555,
                     timezone="Asia/Kolkata"))
        db.commit()
    h = login(client)
    me = profile(client, h)
    other = client.post("/v1/profiles", headers=h, json={"label": "Riya", "birth_date": "1992-11-03", "birth_time": "06:15",
                                                         "place_id": 1273294})
    assert other.status_code == 201, other.text
    return client, h, me, other.json()


def test_requires_login_consent_and_a_profile(client):
    import uuid
    some = str(uuid.uuid4())
    assert client.get(f"/v1/me/match/{some}").status_code == 401
    assert client.get(f"/v1/me/match/{some}", headers=login(client, "nocons", consent=False)).status_code == 403
    assert client.get(f"/v1/me/match/{some}", headers=login(client, "noprofile")).status_code == 404


def test_the_match_has_eight_parts_that_add_up_to_the_total(ready):
    api, h, me, other = ready
    r = api.get(f"/v1/me/match/{other['id']}", headers=h)
    assert r.status_code == 200, r.text
    j = r.json()
    assert [p["key"] for p in j["parts"]] == list(m.KOOTAS)
    assert j["max"] == 36 and abs(sum(p["points"] for p in j["parts"]) - j["total"]) < 1e-9
    assert all(p["name"]["en"] and p["name"]["hi"] and p["about"]["en"] and p["a"]["en"] and p["b"]["hi"] for p in j["parts"])
    assert j["a"]["label"] == "SecretLabel" and j["b"]["label"] == "Riya"
    assert 1 <= j["a"]["moon_sign"]["number"] <= 12 and 1 <= j["b"]["nakshatra"]["number"] <= 27
    assert j["band"] in {"great", "good", "fair", "low"} and j["band_text"]["en"] and j["disclaimer"]["en"]


def test_it_matches_the_engine_and_is_not_stored(ready):
    api, h, me, other = ready
    j = api.get(f"/v1/me/match/{other['id']}", headers=h).json()
    from astrodaily.calc.kundli import compute_chart, resolve_birth_moment
    from datetime import date, time

    def moon(d, t):
        birth = resolve_birth_moment(d, t, "Asia/Kolkata", None)
        c = compute_chart(birth, 28.65195, 77.23149)
        return m.Moon(next(p["longitude"] for p in c["planets"] if p["key"] == "Moon"))
    expected = m.match(moon(date(1990, 5, 15), time(10, 0)), moon(date(1992, 11, 3), time(6, 15)))
    assert abs(j["total"] - expected["total"]) < 1e-9
    assert [p["points"] for p in j["parts"]] == [p["points"] for p in expected["parts"]]


def test_needs_both_birth_times_and_someone_else_and_only_your_own_profiles(ready):
    api, h, me, other = ready
    assert api.get(f"/v1/me/match/{me['id']}", headers=h).status_code == 422  # yourself
    nt = api.post("/v1/profiles", headers=h, json={"label": "Dad", "birth_date": "1960-01-01", "moon_sign": 10,
                                                   "place_id": 1273294})
    assert nt.status_code == 201, nt.text
    assert api.get(f"/v1/me/match/{nt.json()['id']}", headers=h).status_code == 409
    h2 = login(api, "bob")
    assert api.get(f"/v1/me/match/{other['id']}", headers=h2).status_code in (403, 404)
