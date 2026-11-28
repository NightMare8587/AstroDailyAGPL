# Chart meanings (planets, houses, Lagna)

The text behind the cards and rows on the Chart tab. It comes from the backend, inside the chart response
(`GET /v1/profiles/{id}/kundli` and `POST /v1/kundli`): every planet and the Lagna carry a `meaning` with
`about` (what it stands for), `in_sign`, `in_house` (not for the Lagna) and `status`. Each is `{en, hi}`.

- **Where the wording is:** `astrodaily/content/chart_meanings.json`. A reviewer edits that file.
- **How a line is made:** a planet's `in_sign` and `in_house` lines are put together from short parts:
  the planet's themes (`planet_role`), how a sign works (`sign_style`), what a house covers (`house_area`), and
  two templates. The Sun, Moon and Lagna have hand-written lines for each sign (`sign_overrides`) that replace the
  composed `in_sign` line. So a reviewer checks about 60 phrases plus 36 hand-written lines, not 470 sentences.
  The composed lines are formulaic by design; hand-written lines can replace any of them later.
- **Status:** the file has a status per group (`draft` or `reviewed`). A line is `reviewed` only when every group it
  uses is. Everything is `draft` today: written by the model, not checked by a Jyotish reviewer. English and Hindi
  both need review.
- **Showing drafts:** `CHART_MEANINGS_ALLOW_DRAFT` (default true). Set it to false once review is done and any line
  that is still draft disappears from the response, and the app then shows only the facts for it (the rows stop being
  tappable).
- **Checks:** `tests/test_chart_meanings.py` covers all 9 planets x 12 signs x 12 houses plus the Lagna, runs the
  same banned-word check as the content library, and checks the Hindi has no Latin letters.
