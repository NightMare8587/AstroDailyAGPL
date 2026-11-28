"""AI chat with the guide. Personal data: consent required, owner only, deleted with the account."""
import json
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user
from ..billing.service import chat_limit
from ..chat import service as chat
from ..chat.llm import GeminiClient, LlmClient, LlmError
from ..config import get_settings
from ..db import get_db
from ..horoscope.card import DISCLAIMER
from ..models import BirthProfile, ChatConversation, User, primary_profile
from ..ratelimit import limit
from .profile_routes import require_consent

Lang = Literal["en", "hi"]

router = APIRouter(prefix="/v1/chat", tags=["chat"],
                   dependencies=[Depends(limit("chat", "rate_limit_chat_per_minute"))])


def get_llm_client() -> LlmClient | None:
    """None when no API key is configured (the endpoint then answers 503). Tests override this."""
    s = get_settings()
    if not s.gemini_api_key:
        return None
    return GeminiClient(s.gemini_api_key, s.gemini_model, s.chat_max_output_tokens, s.chat_timeout_seconds)


class ConversationIn(BaseModel):
    profile_id: uuid.UUID | None = None  # default: your first profile


class MessageIn(BaseModel):
    text: str
    lang: Lang | None = None  # default: your account language


class MessageOut(BaseModel):
    id: int
    role: str
    text: str
    lang: str
    source: str
    created_at: datetime


class ConversationOut(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID | None
    title: str | None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]


class ReplyOut(BaseModel):
    reply: MessageOut
    remaining_today: int
    disclaimer: dict[str, str]


def _conv_out(c: ChatConversation) -> ConversationOut:
    return ConversationOut(id=c.id, profile_id=c.profile_id, title=c.title, created_at=c.created_at,
                           updated_at=c.updated_at)


def _msg_out(m) -> MessageOut:
    return MessageOut(id=m.id, role=m.role, text=m.text, lang=m.lang, source=m.source, created_at=m.created_at)


def _own(db: Session, user: User, conv_id: uuid.UUID) -> ChatConversation:
    c = db.get(ChatConversation, conv_id)
    if c is None or c.user_id != user.id:  # someone else's conversation looks the same as a missing one
        raise HTTPException(status_code=404, detail="Conversation not found")
    return c


@router.post("/conversations", response_model=ConversationOut, status_code=201)
def create_conversation(body: ConversationIn, user: User = Depends(require_consent),
                        db: Session = Depends(get_db)) -> ConversationOut:
    if body.profile_id is None:
        if not user.profiles:
            raise HTTPException(status_code=409, detail="Create a birth profile first (POST /v1/profiles).")
        profile = primary_profile(user)
    else:
        profile = db.get(BirthProfile, body.profile_id)
        if profile is None or profile.user_id != user.id:
            raise HTTPException(status_code=404, detail="Profile not found")
    count = db.scalar(select(func.count(ChatConversation.id)).where(ChatConversation.user_id == user.id)) or 0
    if count >= get_settings().chat_max_conversations:
        raise HTTPException(status_code=409, detail="Too many conversations. Delete an old one first.")
    c = ChatConversation(user_id=user.id, profile_id=profile.id)
    db.add(c)
    db.commit()
    return _conv_out(c)


@router.get("/conversations", response_model=list[ConversationOut])
def list_conversations(user: User = Depends(require_consent)) -> list[ConversationOut]:
    return [_conv_out(c) for c in user.conversations]


@router.get("/conversations/{conv_id}", response_model=ConversationDetail)
def get_conversation(conv_id: uuid.UUID, user: User = Depends(require_consent),
                     db: Session = Depends(get_db)) -> ConversationDetail:
    c = _own(db, user, conv_id)
    return ConversationDetail(**_conv_out(c).model_dump(), messages=[_msg_out(m) for m in c.messages])


@router.post("/conversations/{conv_id}/messages", response_model=ReplyOut)
def send_message(conv_id: uuid.UUID, body: MessageIn, user: User = Depends(require_consent),
                 db: Session = Depends(get_db), client: LlmClient | None = Depends(get_llm_client)) -> ReplyOut:
    s = get_settings()
    conv = _own(db, user, conv_id)
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Message is empty")
    if len(text) > s.chat_max_message_chars:
        raise HTTPException(status_code=422, detail=f"Message is longer than {s.chat_max_message_chars} characters")
    lang = body.lang or ("hi" if user.language == "hi" else "en")
    try:
        reply = chat.respond(db, user, conv, text, lang, client)
    except chat.DailyLimitReached:
        raise HTTPException(status_code=429, detail="Daily message limit reached. Please come back tomorrow.")
    except LlmError:
        raise HTTPException(status_code=503, detail="The guide is unavailable right now. Please try again shortly.")
    return ReplyOut(reply=_msg_out(reply), remaining_today=max(0, chat_limit(user) - chat.messages_today(db, user)),
                    disclaimer=dict(DISCLAIMER))


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/conversations/{conv_id}/messages/stream")
def send_message_stream(conv_id: uuid.UUID, body: MessageIn, user: User = Depends(require_consent),
                        db: Session = Depends(get_db), client: LlmClient | None = Depends(get_llm_client)):
    """Same as POST .../messages, but the reply arrives as server-sent events while the model writes it:
    ``delta`` {text} (more text), ``replace`` {text} (the finished answer was swapped by the tone check or is a fixed
    safety answer), ``done`` {reply, remaining_today, disclaimer}, or ``error`` {status} if it breaks off (nothing is
    stored then). Problems found before the first word use the same status codes as the plain endpoint."""
    s = get_settings()
    conv = _own(db, user, conv_id)
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Message is empty")
    if len(text) > s.chat_max_message_chars:
        raise HTTPException(status_code=422, detail=f"Message is longer than {s.chat_max_message_chars} characters")
    lang = body.lang or ("hi" if user.language == "hi" else "en")
    events = chat.respond_stream(db, user, conv, text, lang, client)
    try:
        first = next(events)  # fails here, before any output, when the cap is reached or the model is unavailable
    except chat.DailyLimitReached:
        raise HTTPException(status_code=429, detail="Daily message limit reached. Please come back tomorrow.")
    except LlmError:
        raise HTTPException(status_code=503, detail="The guide is unavailable right now. Please try again shortly.")

    def frames():
        pending = first
        while True:
            kind, value = pending
            if kind == "done":
                yield _sse("done", {"reply": _msg_out(value).model_dump(mode="json"),
                                    "remaining_today": max(0, chat_limit(user) - chat.messages_today(db, user)),
                                    "disclaimer": dict(DISCLAIMER)})
            else:
                yield _sse(kind, {"text": value})
            try:
                pending = next(events)
            except StopIteration:
                return
            except (LlmError, chat.DailyLimitReached):
                yield _sse("error", {"status": 503})
                return

    return StreamingResponse(frames(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.delete("/conversations/{conv_id}", status_code=204)
def delete_conversation(conv_id: uuid.UUID, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)) -> None:
    db.delete(_own(db, user, conv_id))
    db.commit()
