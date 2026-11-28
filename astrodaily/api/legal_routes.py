"""Public Terms and Privacy pages, opened inside the app (and readable in any browser).

DRAFT: plain-language text written from what the code actually does (see docs/privacy-and-data.md).
It has not been reviewed by a lawyer and must be before real users sign up. Change LAST_UPDATED when
the text changes, and bump the app's consent version so people are asked again.
"""
from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ..config import get_settings

router = APIRouter(prefix="/legal", tags=["legal"], include_in_schema=False)

LAST_UPDATED = "28 November 2026"

_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{title} · AstroDaily</title>
<style>
:root {{ color-scheme: dark; }}
body {{ margin: 0; background: #07061A; color: #F5F4FF; font: 16px/1.65 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  background-image: radial-gradient(520px 340px at 85% -60px, #3A2B93, transparent 70%); }}
main {{ max-width: 680px; margin: 0 auto; padding: 28px 20px 64px; }}
h1 {{ font-size: 26px; line-height: 1.2; margin: 0 0 6px; letter-spacing: -.01em; }}
h2 {{ font-size: 17px; margin: 30px 0 6px; }}
p, li {{ color: #D9D7F2; }}
ul {{ padding-left: 20px; }}
li {{ margin: 4px 0; }}
.meta {{ color: #9B98C2; font-size: 13px; margin: 0 0 8px; }}
.draft {{ margin: 16px 0 0; padding: 10px 12px; border-radius: 12px; background: #211F40; color: #CDBFFF; font-size: 13px; }}
a {{ color: #8FB4FF; }}
</style></head>
<body><main>
<h1>{title}</h1>
<p class="meta">Last updated {updated}</p>
<p class="draft">This is a plain-language draft. It describes what the app does today and may change before launch.</p>
{body}
</main></body></html>
"""

_TERMS = """
<h2>What AstroDaily is</h2>
<p>AstroDaily gives you a daily Vedic horoscope, good and avoid times for the day, a birth chart, and an AI guide you can ask questions. It is made for reflection and interest.</p>

<h2>It is not advice</h2>
<ul>
<li>Nothing in the app is medical, legal, financial or mental-health advice. Do not use it to decide those things.</li>
<li>Horoscope text, scores and times come from rules that are still being checked by a Jyotish reviewer. They can be wrong.</li>
<li>The guide is an AI, not a person or an astrologer. It can make mistakes. Check anything important yourself.</li>
<li>If you feel unsafe or are thinking of harming yourself, please call Tele-MANAS on 14416, or 112 in an emergency.</li>
</ul>

<h2>Your account</h2>
<ul>
<li>You sign in with Google. Keep your Google account secure; you are responsible for what happens through your account.</li>
<li>Give us your own details, or those of someone who has agreed. Do not use the app to harass, deceive or harm anyone, or to try to break or overload it.</li>
<li>You can delete your account at any time from the Me tab. This removes your account and everything in it, with no recovery.</li>
</ul>

<h2>Your content</h2>
<p>The details and messages you enter remain yours. We use them only to run the app for you, as described in the Privacy Policy.</p>

<h2>The service</h2>
<p>We try to keep AstroDaily available and accurate, but we do not promise it will always work or be error free. We may change or stop features. We may suspend an account that breaks these terms.</p>

<h2>Changes</h2>
<p>If these terms change in a way that matters, the app will tell you and ask you to agree again.</p>
{contact}
"""

_PRIVACY = """
<h2>What we keep</h2>
<ul>
<li><b>Sign-in:</b> your Google account id, email, name and picture link.</li>
<li><b>About you:</b> first name, last name, date of birth, gender (optional), language, and your home city.</li>
<li><b>Birth profiles:</b> the birth date, time and place (with its coordinates) that you enter for yourself or family, up to 5.</li>
<li><b>Chat:</b> the messages you send the guide and its replies, so a conversation can continue.</li>
<li><b>Feedback:</b> thumbs up or down on a day's card, and whether it felt accurate.</li>
<li><b>Reminders:</b> if you turn on daily reminders, your reminder time and your phone's notification token.</li>
<li><b>Consent:</b> which version of these terms you agreed to, and when.</li>
</ul>
<p>We do not store your IP address (it is used briefly in memory to limit abuse), and we hold no payment data.</p>

<h2>Why</h2>
<p>To sign you in, work out your Moon sign and chart, write your daily card, send reminders you asked for, answer your chat questions, and improve the rules and wording.</p>

<h2>Who else sees it</h2>
<ul>
<li><b>Nobody else sees your birth details.</b> We do not sell your data and we show no ads.</li>
<li><b>Google</b> handles sign-in. It also runs the AI model (Gemini) that writes chat answers. Your chat message and the recent conversation go to Gemini, together with a short summary of your day and chart (Moon sign, birth star, ascendant, current period, today's score and times, and your city). We do <b>not</b> send your name, email, birth date, birth time or coordinates.</li>
<li><b>Google (Firebase)</b> delivers push notifications if you turn them on.</li>
<li><b>Railway</b> hosts our servers and database. Data may be stored outside India.</li>
<li>Messages about self-harm are never sent to the model. They get a fixed reply with the Tele-MANAS helpline.</li>
</ul>

<h2>How long we keep it</h2>
<p>Until you delete it. You can delete a birth profile, a chat, or your whole account at any time from the app. Deleting the account removes everything above, with no recovery. We do not yet delete inactive accounts automatically.</p>

<h2>Your choices</h2>
<ul>
<li>See everything we hold about you: the export option in your account.</li>
<li>Change your name, date of birth, gender, language and city in the app.</li>
<li>Turn reminders off, delete a chat or profile, or delete your account.</li>
</ul>

<h2>Security</h2>
<p>Sessions use short-lived tokens, and the app stores them in your phone's secure storage. Traffic to our servers is encrypted. No system is perfectly secure.</p>

<h2>Children</h2>
<p>AstroDaily is not designed for children.</p>
{contact}
"""


def _contact_block() -> str:
    email = get_settings().legal_contact_email
    if not email:
        return ""
    return f"<h2>Questions or complaints</h2>\n<p>Write to <a href=\"mailto:{escape(email)}\">{escape(email)}</a>.</p>"


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(_PAGE.format(title=title, updated=LAST_UPDATED, body=body.format(contact=_contact_block())),
                        headers={"Cache-Control": "public, max-age=300"})


@router.get("/terms")
def terms() -> HTMLResponse:
    return _page("Terms and Conditions", _TERMS)


@router.get("/privacy")
def privacy() -> HTMLResponse:
    return _page("Privacy Policy", _PRIVACY)
