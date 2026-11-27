# Privacy and personal data

Status: draft v0.1 (2026-11-27). This describes what the code does today. It is not a privacy policy
and not legal advice; a lawyer should review it and the policy text before real users sign up
(India's Digital Personal Data Protection Act, 2023, and the app stores' rules both apply).

## What we store

| Data | Where | Why |
|---|---|---|
| Google account id, email, name, picture URL | `users` | Sign-in |
| Language, consent version and time, home place | `users` | App behaviour, proof of consent |
| Refresh tokens (SHA-256 hash only) | `refresh_tokens` | Sessions |
| Horoscope feedback: card (Moon sign or profile), date, thumbs up or down, optional "felt accurate" | `horoscope_feedback` | Tuning the rules and content. Removed with the account, and with the profile when it was a profile's card. |
| Birth profiles: label, birth date and time, birth place and its coordinates and timezone | `birth_profiles` | Charts and daily guidance. Up to 5 per user, so family charts are possible. |

Daily cards are computed on request and not stored. Not stored: IP addresses (used in memory for rate limiting only), chat history (the AI chat is not
built yet), any payment data. `POST /v1/kundli` calculates a chart without saving anything.

## Rules the code enforces

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
