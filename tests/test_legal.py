import pytest

from astrodaily.config import get_settings


@pytest.mark.parametrize("path,title", [("/legal/terms", "Terms and Conditions"), ("/legal/privacy", "Privacy Policy")])
def test_pages_are_public_html(client, path, title):
    r = client.get(path)  # no sign-in needed: the app opens them before anyone has an account
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert f"<h1>{title}</h1>" in r.text
    assert "viewport" in r.text  # readable on a phone


def test_privacy_says_what_the_code_really_does(client):
    t = client.get("/legal/privacy").text
    assert "Gemini" in t and "do <b>not</b> send your name, email, birth date" in t
    assert "Tele-MANAS" in t
    assert "delete a birth profile, a chat, or your whole account" in t


def test_terms_say_it_is_not_advice_and_the_guide_is_an_ai(client):
    t = client.get("/legal/terms").text
    assert "is medical, legal, financial or mental-health advice" in t
    assert "an AI, not a person or an astrologer" in t
    assert "14416" in t


def test_contact_block_only_when_an_address_is_configured(client, monkeypatch):
    assert "Questions or complaints" not in client.get("/legal/privacy").text
    monkeypatch.setenv("LEGAL_CONTACT_EMAIL", "help@example.com")
    get_settings.cache_clear()
    try:
        t = client.get("/legal/privacy").text
        assert 'mailto:help@example.com' in t
        monkeypatch.setenv("LEGAL_CONTACT_EMAIL", '<script>x</script>')
        get_settings.cache_clear()
        assert "<script>x</script>" not in client.get("/legal/terms").text  # escaped
    finally:
        monkeypatch.delenv("LEGAL_CONTACT_EMAIL")
        get_settings.cache_clear()


def test_pages_are_not_in_the_api_docs(client):
    assert "/legal/terms" not in client.get("/openapi.json").text
