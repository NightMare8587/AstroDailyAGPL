"""One chat turn: safety check, build the prompt from the engine's facts, ask the model, check the reply, store."""
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import BirthProfile, ChatConversation, ChatMessage, User
from .context import build_context
from .llm import LlmClient, LlmError, LlmResult, Turn
from .prompt import RETRY_NOTE, SUMMARY_SYSTEM, system_prompt
from .safety import CRISIS_REPLY, FALLBACK_REPLY, breaks_tone_rules, is_crisis

log = logging.getLogger("astrodaily.chat")


class DailyLimitReached(Exception):
    pass


def messages_today(db: Session, user: User, now: datetime | None = None) -> int:
    since = (now or datetime.now(timezone.utc)) - timedelta(hours=24)
    return db.scalar(
        select(func.count(ChatMessage.id)).join(ChatConversation, ChatMessage.conversation_id == ChatConversation.id)
        .where(ChatConversation.user_id == user.id, ChatMessage.role == "user", ChatMessage.created_at >= since)
    ) or 0


def _title(text: str) -> str:
    t = " ".join(text.split())
    return t if len(t) <= 60 else t[:59].rstrip() + "…"


@dataclass
class _Prep:
    crisis: bool
    system: str = ""
    turns: list[Turn] | None = None


def _unsummarised(conv: ChatConversation) -> list[ChatMessage]:
    through = conv.summarized_through
    return [m for m in conv.messages if through is None or m.id > through]


def _prepare(db: Session, user: User, conv: ChatConversation, text: str, lang: str, client: LlmClient | None) -> _Prep:
    """The checks and the prompt, before anything is asked of the model."""
    s = get_settings()
    crisis = is_crisis(text)
    # The daily cap protects cost; it must never stand between a person in distress and the helpline answer.
    if not crisis and messages_today(db, user) >= s.chat_daily_message_limit:
        raise DailyLimitReached
    if crisis:
        return _Prep(True)
    if client is None:
        raise LlmError("not configured")
    profile = db.get(BirthProfile, conv.profile_id) if conv.profile_id else None
    if profile is None:
        raise LlmError("no profile")
    history = [Turn(m.role, m.text) for m in _unsummarised(conv)[-s.chat_history_messages:]]
    return _Prep(False, system_prompt(lang, build_context(user, profile), conv.summary), history + [Turn("user", text)])


def _checked(client: LlmClient, prep: _Prep, result: LlmResult, lang: str) -> tuple[str, str, LlmResult]:
    """The tone check on a finished answer: one retry with a stern note, then a fixed fallback."""
    if breaks_tone_rules(result.text):
        log.info("model reply broke tone rules; retrying once")
        result = client.generate(prep.system + RETRY_NOTE, prep.turns)
    if breaks_tone_rules(result.text):
        return FALLBACK_REPLY[lang], "fallback", result
    return result.text, "model", result


def _store(db: Session, conv: ChatConversation, text: str, lang: str, reply: str, source: str,
           result: LlmResult | None) -> ChatMessage:
    now = datetime.now(timezone.utc)
    conv.messages.append(ChatMessage(role="user", text=text, lang=lang, source="user", created_at=now))
    msg = ChatMessage(role="assistant", text=reply, lang=lang, source=source, model=result.model if result else None,
                      tokens_in=result.tokens_in if result else None, tokens_out=result.tokens_out if result else None,
                      created_at=now + timedelta(microseconds=1))
    conv.messages.append(msg)
    if conv.title is None:
        conv.title = _title(text)
    conv.updated_at = now
    db.commit()
    return msg


def compact(db: Session, conv: ChatConversation, client: LlmClient | None) -> None:
    """When the history reaches its limit, fold the older messages into the conversation's short summary and keep only
    the latest few as they are. A failure here changes nothing: the prompt still only carries the latest messages."""
    s = get_settings()
    pending = _unsummarised(conv)
    if client is None or len(pending) < s.chat_history_messages:
        return
    old = pending[:-s.chat_compact_keep_messages] if s.chat_compact_keep_messages > 0 else pending
    if not old:
        return
    lines = ([f"EXISTING SUMMARY:\n{conv.summary}\n"] if conv.summary else []) + ["NEW MESSAGES:"]
    lines += [f"{'Person' if m.role == 'user' else 'Guide'}: {m.text}" for m in old]
    try:
        result = client.generate(SUMMARY_SYSTEM, [Turn("user", "\n".join(lines))])
    except LlmError:
        log.info("could not summarise the chat; keeping the latest messages only")
        return
    conv.summary, conv.summarized_through = result.text, old[-1].id
    db.commit()


def respond(db: Session, user: User, conv: ChatConversation, text: str, lang: str, client: LlmClient | None
            ) -> ChatMessage:
    """Store the user's message and the reply, and return the reply. Raises DailyLimitReached, or LlmError when
    the model is unavailable (in which case nothing is stored, so the person can simply try again)."""
    prep = _prepare(db, user, conv, text, lang, client)
    if prep.crisis:
        msg = _store(db, conv, text, lang, CRISIS_REPLY[lang], "safety", None)
    else:
        reply, source, result = _checked(client, prep, client.generate(prep.system, prep.turns), lang)
        msg = _store(db, conv, text, lang, reply, source, result)
    compact(db, conv, client)
    return msg


def respond_stream(db: Session, user: User, conv: ChatConversation, text: str, lang: str, client: LlmClient | None
                   ) -> Iterator[tuple[str, object]]:
    """The same turn as ``respond``, as events: ("delta", text) while the model writes, ("replace", text) if the tone
    check swaps the finished answer for another, then ("done", the stored reply). Nothing is stored unless it finishes."""
    prep = _prepare(db, user, conv, text, lang, client)
    if prep.crisis:
        msg = _store(db, conv, text, lang, CRISIS_REPLY[lang], "safety", None)
        yield "replace", msg.text
        yield "done", msg
        compact(db, conv, client)
        return
    result = None
    for piece in client.stream(prep.system, prep.turns):
        if isinstance(piece, LlmResult):
            result = piece
        else:
            yield "delta", piece
    streamed = result.text
    reply, source, result = _checked(client, prep, result, lang)
    if reply != streamed:
        yield "replace", reply
    msg = _store(db, conv, text, lang, reply, source, result)
    yield "done", msg
    compact(db, conv, client)
