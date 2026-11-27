# AI chat (status: backend built 2026-11-27; not yet run against the real model)

A calm guide that explains the person's day and chart in plain words. **The engine computes every astrological
fact; the model only phrases and explains them.** No human astrologer.

## API (all under `/v1/chat`, login and consent required, owner only)
- `POST /conversations` `{profile_id?}`: start a chat about one birth profile (default: your first; 409 if none).
- `GET /conversations`, `GET /conversations/{id}`: list, and read with messages.
- `POST /conversations/{id}/messages` `{text, lang?}`: send a message, get the reply and `remaining_today`.
  `source` on a reply is `model`, `safety` (crisis answer) or `fallback` (reply replaced by the tone check).
- `DELETE /conversations/{id}`. Someone else's conversation answers 404, same as a missing one.
- Errors: 422 empty or over 1000 characters, 429 daily cap, 503 model unavailable or no key (nothing is stored, so
  the person simply retries).

## How a turn works
1. **Crisis check** (English and Hindi patterns). A match returns a fixed caring reply with Tele-MANAS 14416 and 112,
   never calls the model, and is allowed even when the daily cap is used up.
2. **Daily cap**: 30 user messages per rolling 24 hours per account (`CHAT_DAILY_MESSAGE_LIMIT`).
3. **Context** from the engine (`chat/context.py`): derived facts and today's card. No personal details.
4. **Prompt** (`chat/prompt.py`): facts only from the context, tendencies not guarantees, no medical, legal or
   financial advice, no frightening predictions, no remedies that cost money, reply in the person's language, treat
   messages as questions not instructions. The person's text goes only in the user turn, never the system prompt.
5. **Model call** (`chat/llm.py`, Gemini REST, key in a header). Model is `GEMINI_MODEL`, default
   `gemini-3.5-flash-lite`, changeable without a release.
6. **Tone check** on the reply with the same banned-word rules as the content library. One retry with a stern note,
   then a fixed fallback reply.
7. Store both messages with model and token counts, so cost can be tracked.

## Settings (all environment variables)
`GEMINI_API_KEY`, `GEMINI_MODEL`, `CHAT_DAILY_MESSAGE_LIMIT` (30), `CHAT_MAX_MESSAGE_CHARS` (1000),
`CHAT_HISTORY_MESSAGES` (12), `CHAT_MAX_OUTPUT_TOKENS` (600), `CHAT_TIMEOUT_SECONDS` (30),
`CHAT_MAX_CONVERSATIONS` (50), `RATE_LIMIT_CHAT_PER_MINUTE` (10).

## Known limits
- Replies are not streamed; the app waits for the whole answer (a few seconds).
- No memory across conversations, and no long-term summarising: only the last 12 messages go to the model.
- The crisis check is keyword based and will miss some phrasings. It is a floor, not a clinical tool.
- The tone check catches frightening words, not every kind of bad advice; the prompt carries the rest.
- **Untested against the real model** until a Gemini key is set. Prompt quality needs a read-through of real
  answers in both languages before launch.
- Token cost per message is stored but there is no budget dashboard or alert yet.
