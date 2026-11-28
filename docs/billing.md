# Subscriptions (status: built 2026-11-29 with a fake store; Google Play not connected yet)

## What is free and what is paid
| Free | Paid (monthly 49 rupees, yearly 399 rupees, 7-day free trial) |
|---|---|
| Chart, planets, yogas | Good time and go-easy time windows |
| Today's and tomorrow's score, area bars, suggestions | Written horoscope paragraph and the planet cards |
| Calendar: past days, today and tomorrow | Calendar days after tomorrow |
| Chat: 5 messages in a rolling 24 hours | Chat: 30 messages |

Limits are settings (`CHAT_FREE_DAILY_MESSAGE_LIMIT`, `FREE_CALENDAR_DAYS_AHEAD`, `DAILY_HOROSCOPE_REQUIRES_PREMIUM`), so
they change without a release. Not gated yet: the love reading (a partner's chart does not exist yet).
The paid parts are enforced on the server: a free account gets `402 premium_required` for a day after tomorrow, for the
written horoscope and for the planet cards; the card, widget and daily push leave the time windows out; the month view
returns later days as `locked: true` (score 0, tithi and festivals still shown, they are the same for everyone).

## API
- `GET /v1/plans` (public): `{provider, plans: [{id, period_days, price_inr, trial_days}]}`. `provider` is `none`,
  `fake` or later `google`.
- `GET /v1/me/subscription`: `{premium, plan, expires_at, auto_renewing, trial, provider}`.
- `POST /v1/me/subscription` `{product_id: monthly|yearly, purchase_token}`: the server checks the token with the
  store; the app's word is not enough. The same token again changes nothing; a token already used by another account is
  409; a token the store does not know is 422; with no store configured it is 503.
- `POST /v1/me/subscription/fake/cancel` and `/fake/expire`: test store only (404 otherwise).

## Who is premium
Anyone with a subscription row that is not revoked and has not expired (`billing/service.py`). The expiry date is the
server's: the app only reads it. Cancelling in the store sets `auto_renewing` false and access runs to `expires_at`;
a refund sets `revoked_at` and ends access at once. A written horoscope saved during a subscription is hidden again
once it ends.

## The fake store (`BILLING_PROVIDER=fake`)
A purchase token `fake:<plan>:<trial|paid>:<anything>` is believed. **Anyone can make one, so the fake store must not
be on in production with real users.** The default is `none`: purchases are refused.

## To connect Google Play (needs you)
1. Create the subscription products in Play Console: `monthly` (49 rupees) and `yearly` (399 rupees), each with a
   7-day free trial. The app must be uploaded to at least internal testing before purchases work.
2. Give a service account access to the Play Developer API (Play Console, API access) and set its JSON on Railway.
3. Still to build: a `google` verifier that calls the Play Developer API (`purchases.subscriptionsv2.get`) with the
   token, the app side using the Play billing library, and the notifications Google sends on renewal, cancellation
   and refund (real-time developer notifications), so expiry and refunds are seen without the app being open.
