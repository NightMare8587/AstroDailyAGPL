# Notifications (status: backend built 2026-11-27, nothing sent yet)

One message kind for now: **the daily card**, sent at a local time the user picks (default 07:30), off until
they opt in. It shows the first suggestion in the user's language and the best time window.

## API (all under `/v1/me`, login required; writing needs consent)
- `GET /notifications`: daily on/off, time, language, devices (no tokens), `ready_to_send`.
- `PUT /notifications` `{daily_enabled?, daily_time?}`: opt in or out, choose the time (local, `HH:MM`).
- `POST /devices` `{token, platform: android|ios|web}`: register the FCM token. Same token again refreshes it;
  a token that was on another account moves here (a token belongs to the phone). Max 10 per account.
- `DELETE /devices/{id}`: remove one. Someone else's device returns 404.
- `GET /export` now lists notification settings and devices, never the tokens.
- Deleting the account removes devices, settings and send history.

## How delivery works
`python -m astrodaily.tools.send_notifications [--dry-run]` is a separate run, started every 5 to 10 minutes by a
scheduler, never inside the web process. For each opted-in, consented user with a birth profile and an active
device it asks: has this user's send time passed in their own timezone (home city, else birth place), within
`NOTIFY_MAX_LATE_MINUTES` (default 180)? If so it **claims** that local day in `notification_log` (unique per
user, kind and date), builds the card (same wording and rotation as the app), sends to every active device,
and records `sent` or `failed`. Failed sends retry on the next runs, 3 attempts in all. A token that FCM says
is dead is disabled. Four concurrent runs against Postgres sent exactly one message.

`--dry-run` works out who would be messaged and writes and sends nothing.

## Privacy
Lock screens are public: the message holds one suggestion line and a time window, no name, no birth details. The
data payload is only `type`, `date`, `score`. The log keeps no message text.

## To go live (needs you)
1. Create a Firebase project and a service account with the Cloud Messaging role; set its JSON as
   `FCM_SERVICE_ACCOUNT_JSON` on Railway. Until then the run only logs.
2. Add a Railway cron service from the same image with start command
   `python -m astrodaily.tools.send_notifications` and schedule `*/5 * * * *`.
3. The Flutter app registers its token after login and consent (`POST /v1/me/devices`).

## Not built yet
Other message kinds (Rahu Kaal heads-up, special days, ingress alerts), quiet hours, per-kind switches,
and delivery metrics.
