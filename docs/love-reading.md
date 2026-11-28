# Love and partnership reading

`GET /v1/me/reading/love?lang=en|hi` returns a short written reading about how the person tends to love and what they
tend to look for in a partner. It needs consent and a birth profile with a birth time (without one: 409).

## How it is made

1. The engine works out the chart facts (`horoscope/love_reading.facts`): the Lagna, the 7th house and its lord and
   where that lord sits, planets in the 7th, Venus, the Darakaraka (the planet with the fewest degrees in its sign,
   in the common seven-karaka scheme), and the Navamsa Lagna, its 7th house and where Venus is in the Navamsa.
2. The model (Gemini, same client as the daily horoscope) writes one paragraph from those facts only. The prompt
   (`chat/prompt.py`, `LOVE_SYSTEM`) forbids predicting when or whether someone marries, describing a partner, saying
   anyone is or is not a soulmate, and anything frightening. The reply goes through the same tone check, retried once.
3. It is saved once per profile and language (`love_readings`), so it costs nothing on later opens and does not change.
   It is removed when the birth details change, with the profile, or with the account, and it is in the export.

The response also carries `facts` (the Lagna, the 7th house sign and its lord, the planets in the 7th, Venus, and the
Navamsa Lagna and 7th house) as plain data, so the app can show them as icons beside the paragraph. They are worked out
on each request and not stored.

No name, birth date, birth time or coordinates are sent to the model. The rules behind the facts are common
convention and have not been reviewed by a Jyotish expert; the status stays `draft` until they are.

## Divisional charts

`/v1/kundli` also returns `saptamsa_sign` (D7, children) and `dashamsa_sign` (D10, career) beside `navamsa_sign` for the
Lagna and every planet. D7: odd signs count from themselves, even signs from the 7th sign. D10: odd signs count from
themselves, even signs from the 9th sign. The Moon chart needs no new field: it is the same planets with the Moon's
sign as house 1.
