# Home-screen widget: background refresh

The Android widget shows a picture the app draws (score, Moon sign, a line from today's horoscope, the good time).
It stays fresh without the app being opened through a background job on the phone. That job must not use the
session: refresh tokens rotate, and showing the server a used one revokes every session of the account, so a job that
raced the app could sign the person out everywhere. It uses its own narrow token instead.

- `POST /v1/me/widget-token` (signed in, consent): returns a **widget token**. JWT type `widget`, valid
  `WIDGET_TOKEN_DAYS` days (30). The app asks again each time it is opened, so it only lapses after a month unused.
- `GET /v1/widget/card?lang=` (widget token only): today's card for the person's own profile: score, headline, good and
  Rahu Kaal windows, Moon sign, and the written paragraph (built once and shared with the Today tab, see
  `docs/daily-horoscope.md`; `null` when the model is unavailable). Needs consent, like every personal endpoint.
- A widget token opens nothing else, and a session token is refused here (they are different JWT types).
- **Sign-out revokes it:** `POST /v1/auth/logout` sets `users.widget_tokens_revoked_before`; tokens issued before that
  moment are refused (microsecond `t` claim). Signing in again and asking again gives a working one. The app also
  deletes its copy and clears the widget when the person signs out.
- It reads personal derived data (Moon sign, score, paragraph) and no birth details. Treat the token like a password
  for the widget card only.

## The planet widget

`GET /v1/widget/planets?lang=` (widget token) returns the same five planet cards as `GET /v1/me/horoscope/planets`, for
today, so the "Planet card" widget can refresh in the background. It builds and saves them the first time, like the app.
Without a birth time it answers 409.
