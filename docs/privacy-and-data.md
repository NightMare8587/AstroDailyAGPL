# Privacy and personal data

Status: draft v0.1 (2026-11-27). This describes what the code does today. It is not a privacy policy
and not legal advice; a lawyer should review it and the policy text before real users sign up
(India's Digital Personal Data Protection Act, 2023, and the app stores' rules both apply).

## What we store

| Data | Where | Why |
|---|---|---|
| Google account id, email, name, picture URL | `users` | Sign-in |
| First name, last name, date of birth, gender (optional) | `users` | Setup page after sign-in; changeable, deleted and exported with the account |
| Language, consent version and time, home place | `users` | App behaviour, proof of consent |
| Refresh tokens (SHA-256 hash only) | `refresh_tokens` | Sessions |
| Horoscope feedback: card (Moon sign or profile), date, thumbs up or down, optional "felt accurate" | `horoscope_feedback` | Tuning the rules and content. Removed with the account, and with the profile when it was a profile's card. |
| Chat messages (what you typed and the guide answered), per conversation, with the model used and token counts | `chat_conversations`, `chat_messages` | The AI chat's history, so a conversation can continue. Removed with the account, with the profile it was about, or when you delete the conversation. Included in the export. |
| When you sent each message to the guide (time only, no text) | `chat_usage` | Keeps the daily message limit honest when a chat is deleted. Removed with the account. Not in the export (it holds no content, only timestamps). |
| Your subscriptions: plan, when it ends, whether it renews, the store's purchase token | `subscriptions` | Decides what you can open. Removed with the account. Included in the export, except the purchase token (it is a credential for the store). No card or payment details are ever held here: the store keeps those. |
| Written daily horoscope (the paragraph shown on the Today tab), per profile, day and language, with the model used and token counts | `daily_horoscopes` | Built once by the model the first time a day is opened, then kept so it does not change that day. Removed with the account, with the profile, or when birth details change. Included in the export. Status `draft` until reviewed. |
| Written love and partnership reading, per profile and language, with the model used and token counts | `love_readings` | Built once by the model the first time it is opened, then kept (it comes from the birth chart, so it is the same every day). Removed with the account, with the profile, or when birth details change. Included in the export. Status `draft` until reviewed. |
| Birth profiles: label, birth date and time, birth place and its coordinates and timezone | `birth_profiles` | Charts and daily guidance. Up to 5 per user, so family charts are possible. |

Daily cards are computed on request and not stored (only the written paragraph is). Not stored: IP addresses (used in memory for rate limiting only), any payment data. `POST /v1/kundli` calculates a chart without saving anything.

## Rules the code enforces

- **How consent is recorded.** There is no separate consent page. The launch screen says "By continuing you agree to
  our Terms and Conditions and Privacy Policy" (both open in the app), and the first save on the setup page records the
  consent version and time. A "?" on the setup page explains what we keep and why. **This is implied consent ("by
  continuing"): a lawyer must confirm it is enough under the DPDP Act, or whether an explicit tick is needed.**
- **Consent first.** Every `/v1/profiles` endpoint answers 403 until the user has recorded consent
  (`PATCH /v1/me` with `consent_version`). The version and time are stored.
- **Owner only.** A profile is visible only to its owner. Another user's profile id answers 404,
  the same as a profile that does not exist. Ids are random UUIDs.
- **Deletion.** `DELETE /v1/profiles/{id}` removes one profile. `DELETE /v1/me` removes the account,
  its sessions and all its profiles, in one step, with no recovery.
- **Export.** `GET /v1/me/export` returns everything held about the signed-in user (including horoscope feedback), and works even
  before consent.
- **No birth data in URLs.** Profile charts are read with `GET /v1/profiles/{id}/kundli`; birth
  details travel in request bodies, so they do not appear in access logs.
- **Place snapshot.** A profile keeps a copy of its place's coordinates, so a chart does not change if
  the place data is re-imported.

## Decisions taken (change them if you disagree)

- **Retention:** profiles are kept until the user deletes them or the account. There is **no
  automatic deletion of inactive accounts yet.** Decide a period (for example, delete after 24
  months of inactivity, with a warning email) and add a scheduled job.
- **Consent text:** not written yet. It should say what is collected, why, that chat messages go to
  Google's Gemini to generate answers, and how to delete everything.
- **Third parties:** Google (sign-in, and Gemini once the chat exists), Railway (hosting and database).
  Use a paid Gemini key in production: the free tier says data may be used to improve Google's products.
- **Storage region:** Railway's database region (not checked); birth data may leave India.

## Not done

- Encryption of birth data beyond what the hosting provider does for the database volume.
- Automatic deletion of inactive accounts; an audit log of who accessed what.
- Parental consent for minors, a grievance contact, breach-notification process.
- Tying consent to a specific policy document (only a version string is stored).

## AI chat and the model provider (Google Gemini)

The written daily horoscope uses the same provider and the same derived facts (no name, birth date, birth time or coordinates), with no typed text. See `docs/daily-horoscope.md`. The love reading does the same with chart facts only; see `docs/love-reading.md`.

- **What leaves our server:** the person's typed message, the last 12 messages of that conversation, and a short
  context of *derived* facts: Moon sign, birth star, ascendant, running dasha, today's day score and suggestions,
  good and avoid times, panchang, and the city used for today's times. **Not sent:** name, email, birth date,
  birth time, coordinates, or the profile label.
- **Who processes it:** Google, through the Gemini API with our key. Use a **paid-tier** API key: Google's terms
  for free-tier keys allow using content to improve its products, paid-tier terms do not. Confirm the current
  terms before launch, and describe this processor in the privacy policy.
- **Crisis messages** (self-harm, suicide) are answered with a fixed message and the Tele-MANAS helpline and are
  never sent to the model.
- **Open decision:** how long chat history is kept for inactive accounts (same question as profiles).
