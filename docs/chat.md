# AI chat (status: backend built 2026-11-27; run against the real model 2026-11-28)

A calm guide that explains the person's day and chart in plain words. **The engine computes every astrological
fact; the model only phrases and explains them.** No human astrologer.

## API (all under `/v1/chat`, login and consent required, owner only)
- `POST /conversations` `{profile_id?}`: start a chat about one birth profile (default: your first; 409 if none).
- `GET /conversations`, `GET /conversations/{id}`: list, and read with messages.
- `POST /conversations/{id}/messages` `{text, lang?}`: send a message, get the reply and `remaining_today`.
  `source` on a reply is `model`, `safety` (crisis answer) or `fallback` (reply replaced by the tone check).
- `POST /conversations/{id}/messages/stream` `{text, lang?}`: the same turn, but the reply arrives as server-sent events
  while the model writes it: `delta` `{text}`, `replace` `{text}` (the finished answer was swapped by the tone check, or is
  the fixed safety answer), `done` `{reply, remaining_today, disclaimer}`, or `error` `{status}` if it breaks off (nothing is
  stored then). The cap, an unavailable model and bad input answer 429, 503 and 422 before any output, as above.
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
5. **Model call** (`generate`, or `stream` for the streaming endpoint) (`chat/llm.py`, Gemini REST, key in a header). Model is `GEMINI_MODEL`, default
   `gemini-3.5-flash-lite`, changeable without a release.
6. **Tone check** on the reply with the same banned-word rules as the content library. One retry with a stern note,
   then a fixed fallback reply.
7. **Compaction**: once the messages not yet summarised reach `CHAT_HISTORY_MESSAGES`, all but the latest
   `CHAT_COMPACT_KEEP_MESSAGES` are folded (with any earlier summary) into a short summary kept on the conversation
   (`summary`, `summarized_through`). The model then sees that summary plus the unsummarised messages, so the prompt
   stays bounded and the thread is not lost. A failed summary changes nothing. The summary is personal data: it is in
   the export and goes with the conversation.
8. Store both messages with model and token counts, so cost can be tracked.

## Settings (all environment variables)
`GEMINI_API_KEY`, `GEMINI_MODEL`, `CHAT_DAILY_MESSAGE_LIMIT` (30), `CHAT_MAX_MESSAGE_CHARS` (1000),
`CHAT_HISTORY_MESSAGES` (12, also the point where older messages are summarised), `CHAT_COMPACT_KEEP_MESSAGES` (4), `CHAT_MAX_OUTPUT_TOKENS` (600), `CHAT_TIMEOUT_SECONDS` (30),
`CHAT_MAX_CONVERSATIONS` (50), `RATE_LIMIT_CHAT_PER_MINUTE` (10).

## Known limits
- Streaming shows words before the tone check has seen the whole answer. If the check rejects it, the text on screen is
  swapped for the fallback (`replace`); a banned word can show for a moment.
- No memory across conversations. Within one, older messages are only as good as their short summary.
- The crisis check is keyword based and will miss some phrasings. It is a floor, not a clinical tool.
- The tone check catches frightening words, not every kind of bad advice; the prompt carries the rest.
- **Run against real Gemini once** (13 questions, English and Hindi): answers stayed grounded in the engine's
  times and score, declined medical, financial, gemstone, prompt-leak and off-topic requests, and never predicted
  harm. That run found two problems, both fixed: the crisis check missed "ending my life" (patterns now cover
  -ing and -ed forms and more Hindi phrasings), and the model once said "4 में से 4" for a score out of 5 (the
  prompt now fixes the scale). A human should still read more answers in both languages before launch.
- Token cost per message is stored but there is no budget dashboard or alert yet.
