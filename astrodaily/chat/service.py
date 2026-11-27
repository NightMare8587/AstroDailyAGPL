"""One chat turn: safety check, build the prompt from the engine's facts, ask the model, check the reply, store."""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import BirthProfile, ChatConversation, ChatMessage, User
from .context import build_context
from .llm import LlmClient, LlmError, Turn
from .prompt import RETRY_NOTE, system_prompt
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


def respond(db: Session, user: User, conv: ChatConversation, text: str, lang: str, client: LlmClient | None
            ) -> ChatMessage:
    """Store the user's message and the reply, and return the reply. Raises DailyLimitReached, or LlmError when
    the model is unavailable (in which case nothing is stored, so the person can simply try again)."""
    s = get_settings()
    crisis = is_crisis(text)
    # The daily cap protects cost; it must never stand between a person in distress and the helpline answer.
    if not crisis and messages_today(db, user) >= s.chat_daily_message_limit:
        raise DailyLimitReached

    source, model, tin, tout = "safety", None, None, None
    if crisis:
        reply = CRISIS_REPLY[lang]
    else:
        if client is None:
            raise LlmError("not configured")
        profile = db.get(BirthProfile, conv.profile_id) if conv.profile_id else None
        if profile is None:
            raise LlmError("no profile")
        history = [Turn(m.role, m.text) for m in conv.messages[-s.chat_history_messages:]]
        turns = history + [Turn("user", text)]
        system = system_prompt(lang, build_context(user, profile))
        result = client.generate(system, turns)
        if breaks_tone_rules(result.text):
            log.info("model reply broke tone rules; retrying once")
            result = client.generate(system + RETRY_NOTE, turns)
        if breaks_tone_rules(result.text):
            reply, source = FALLBACK_REPLY[lang], "fallback"
        else:
            reply, source = result.text, "model"
        model, tin, tout = result.model, result.tokens_in, result.tokens_out

    now = datetime.now(timezone.utc)
    conv.messages.append(ChatMessage(role="user", text=text, lang=lang, source="user", created_at=now))
    msg = ChatMessage(role="assistant", text=reply, lang=lang, source=source, model=model, tokens_in=tin,
                      tokens_out=tout, created_at=now + timedelta(microseconds=1))
    conv.messages.append(msg)
    if conv.title is None:
        conv.title = _title(text)
    conv.updated_at = now
    db.commit()
    return msg
