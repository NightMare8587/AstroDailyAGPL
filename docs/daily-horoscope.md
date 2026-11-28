# Written daily horoscope

The paragraph on the Today tab. Endpoint: `GET /v1/me/horoscope/text?date=&lang=` (consent required, own primary
profile). Allowed days: today and tomorrow in the person's day location; other days answer 422.

- **How it is made:** Gemini writes one paragraph (about 90 to 130 words) from the engine's derived facts (the same
  context the chat uses, `chat/context.py`). Instructions: `DAILY_SYSTEM` in `chat/prompt.py`. The reply goes through
  the same tone check as chat; if it still breaks the rules after one retry nothing is saved and the endpoint
  answers 503 (a stand-in would otherwise stay for the whole day).
- **Saved once:** table `daily_horoscopes`, one row per profile, day and language. Opening it again returns the same
  text with no model call. Two opens at once end with the same text (unique constraint). Birth details changing
  (profile edit or setup again) deletes that profile's saved rows, because they were written from the old details.
- **Status:** every row is `draft` until a reviewer approves the wording. The app shows it as is for now.
- **Free limit (config, off):** `DAILY_HOROSCOPE_FREE_LIMIT` = number of days of written horoscope a person gets
  free; `0` (default) means no limit. Past the limit the endpoint answers 402. This is the hook for a later Pro plan.
- **Other settings:** `DAILY_HOROSCOPE_MAX_OUTPUT_TOKENS` (900), plus the existing `GEMINI_API_KEY`, `GEMINI_MODEL`.
  Use a paid-tier key (see privacy doc).
- **Later idea:** a cron that writes tomorrow's horoscope ahead of time for active users. Not built.
