# Festival calendar (status: built 2026-11-28, draft until a panchang reviewer signs off)

`GET /v1/me/horoscope/month` now carries `festivals` on each day: a list of `{en, hi}` names, empty on most days.
The dates are worked out from the Sun and Moon for the user's home city (else birth place); nothing is stored.

## How a date is found (`astrodaily/calc/festivals.py`)
- Each festival is a lunar month, a paksha, a tithi number and a **kala** (part of the day): sunrise, late morning,
  midday, afternoon, evening (pradosh) or midnight. The festival falls on the first day whose kala lies inside that tithi.
- Months run new moon to new moon (amanta), named by the sign the Sun is in at the start (Sun in Pisces -> Chaitra).
  A month with no sankranti is the extra month and is skipped, so 2026's extra Jyeshtha does not pull Rath Yatra early.
- Diwali takes the **second** day when the new-moon tithi covers the evening on two days running.
- Raksha Bandhan is not kept while Bhadra (Vishti karana) runs in the afternoon; it moves to the next day.
- Makar Sankranti is the day the Sun enters sidereal Capricorn; if that is after sunset, the next day.

## Checked against
Drik Panchang for New Delhi, years 2024 to 2027 (read 2026-11-28): every festival kept here matches (100 of 100
compared). Some late-October to November entries for 2024 to 2027 came from a model's summary of the page, not the
page text. The 2026 list is pinned in `tests/test_festivals.py`.

## Left out on purpose (need a reviewer to choose a rule)
- **Janmashtami**: Smarta and Vaishnava dates differ and depend on Rohini nakshatra.
- **Holika Dahan and Holi**: the Bhadra rule gave the right day in 2024 to 2026 and one day late in 2027.
- **Dev Uthani Ekadashi**: Smarta and Vaishnava dates differ in some years (2025).
- Regional festivals (Onam, Pongal, Bihu, Durga Puja days by region), Jayantis, and Ekadashi names.
Ekadashi, Pradosh, Sankashti and Purnima are still marked by the existing `special` field.

## Not done
Purnimanta month names (North India names the dark half after the following month) are not shown; the table uses
amanta only. Dates are for the user's own city, so a festival after sunset or near midnight can differ by a day
from another city's almanac.
