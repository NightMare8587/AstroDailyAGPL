import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import (
    CheckConstraint, Text, Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, JSON, SmallInteger, String, Time, UniqueConstraint, Uuid,
)
from sqlalchemy import false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    google_sub: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320))
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Filled in by the person on the setup page after sign-in (the Google name is only a suggestion).
    first_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)  # female | male | other; optional
    picture_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    language: Mapped[str] = mapped_column(String(2), default="en")  # "en" or "hi"
    # Consent to the privacy policy / data use. Null until the user accepts.
    consent_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Widget tokens issued before this moment are refused (set on sign-out).
    widget_tokens_revoked_before: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # The user's home city, picked once from place search. Cleared automatically if the place is removed.
    home_place_id: Mapped[int | None] = mapped_column(
        ForeignKey("places.id", ondelete="SET NULL"), nullable=True
    )
    home_place: Mapped["Place | None"] = relationship(lazy="joined")

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    profiles: Mapped[list["BirthProfile"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="BirthProfile.created_at"
    )
    feedback: Mapped[list["HoroscopeFeedback"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="HoroscopeFeedback.created_at"
    )
    devices: Mapped[list["DeviceToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="DeviceToken.created_at"
    )
    notification_prefs: Mapped["NotificationPrefs | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    conversations: Mapped[list["ChatConversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="ChatConversation.updated_at.desc()"
    )
    daily_horoscopes: Mapped[list["DailyHoroscope"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="DailyHoroscope.local_date.desc()"
    )
    love_readings: Mapped[list["LoveReading"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    planet_cards: Mapped[list["DailyPlanetCards"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    match_summaries: Mapped[list["MatchSummary"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    chat_usage: Mapped[list["ChatUsage"]] = relationship(cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)  # SHA-256 hex; raw token is never stored
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="refresh_tokens")


class Place(Base):
    """A populated place from GeoNames (CC BY 4.0). Coordinates may be stored permanently."""
    __tablename__ = "places"
    __table_args__ = (
        Index("ix_places_name_hi", "name_hi", postgresql_ops={"name_hi": "text_pattern_ops"}),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)  # GeoNames id
    name: Mapped[str] = mapped_column(String(200))
    name_hi: Mapped[str | None] = mapped_column(String(200), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    district: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country_code: Mapped[str] = mapped_column(String(2), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    population: Mapped[int] = mapped_column(Integer, default=0)
    timezone: Mapped[str] = mapped_column(String(64))  # IANA name, e.g. Asia/Kolkata


class PlaceName(Base):
    """Searchable (normalised) names for a place: its name, ASCII name, alternate and Hindi names."""
    __tablename__ = "place_names"
    __table_args__ = (
        Index("ix_place_names_name_norm", "name_norm", postgresql_ops={"name_norm": "text_pattern_ops"}),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"), index=True)
    name_norm: Mapped[str] = mapped_column(String(200))


class BirthProfile(Base):
    """A person's birth details (the user's own, or a family member's). Personal data: it is deleted
    with the account, and only its owner can read it."""
    __tablename__ = "birth_profiles"
    __table_args__ = (
        # Without a birth time the Moon sign must be stored, or the daily card and chat have nothing to work from.
        CheckConstraint("birth_time IS NOT NULL OR (moon_sign IS NOT NULL AND moon_sign BETWEEN 1 AND 12)", name="ck_birth_profiles_time_or_sign"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(40))
    birth_date: Mapped[date] = mapped_column(Date)
    # Null when the person does not know their birth time. Then the Moon sign is stored in moon_sign
    # (worked out from the date, or chosen by the person from the two possible signs).
    birth_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    moon_sign: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    # The place is copied in, so a chart never changes if GeoNames data is later re-imported or the
    # place disappears. place_id is only a pointer back to the picked place.
    place_id: Mapped[int | None] = mapped_column(ForeignKey("places.id", ondelete="SET NULL"), nullable=True)
    place_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    timezone: Mapped[str] = mapped_column(String(64))  # IANA name
    utc_offset_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)  # overrides timezone
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="profiles")
    feedback: Mapped[list["HoroscopeFeedback"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["ChatConversation"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    daily_horoscopes: Mapped[list["DailyHoroscope"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    love_readings: Mapped[list["LoveReading"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    planet_cards: Mapped[list["DailyPlanetCards"]] = relationship(back_populates="profile", cascade="all, delete-orphan")


class HoroscopeFeedback(Base):
    """A thumbs up or down on one day's card. One row per user, card and date (re-rating replaces it).
    Removed with the account, and with the profile when the card was a profile's."""
    __tablename__ = "horoscope_feedback"
    __table_args__ = (UniqueConstraint("user_id", "subject", "local_date", name="uq_feedback_user_subject_date"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("birth_profiles.id", ondelete="CASCADE"), nullable=True, index=True
    )
    subject: Mapped[str] = mapped_column(String(48))  # "rashi:5" or "profile:<uuid>"
    local_date: Mapped[date] = mapped_column(Date)
    rating: Mapped[int] = mapped_column(SmallInteger)  # +1 or -1
    felt_accurate: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    engine_version: Mapped[str] = mapped_column(String(16))
    ruleset_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="feedback")
    profile: Mapped["BirthProfile | None"] = relationship(back_populates="feedback")


class ContentSnippet(Base):
    """One line of wording for one signal, language and variant. Only ``reviewed`` rows reach users
    (``draft`` too when CONTENT_ALLOW_DRAFT is on). Loaded from the private content repo by
    ``tools/import_content.py``; never edited by hand."""
    __tablename__ = "content_snippets"
    __table_args__ = (
        UniqueConstraint("signal_key", "lang", "kind", "variant", name="uq_content_snippet"),
        Index("ix_content_lookup", "signal_key", "lang", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    signal_key: Mapped[str] = mapped_column(String(64))
    lang: Mapped[str] = mapped_column(String(2))
    kind: Mapped[str] = mapped_column(String(16), default="line")
    variant: Mapped[int] = mapped_column(SmallInteger)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), default="draft")
    version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class DeviceToken(Base):
    """A phone or browser that can receive push messages (an FCM registration token). Personal data:
    removed with the account, and disabled when the push service says the token is dead."""
    __tablename__ = "device_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(4096), unique=True)
    platform: Mapped[str] = mapped_column(String(8))  # android, ios or web
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="devices")


class NotificationPrefs(Base):
    """What a user wants to be sent. Off until they opt in."""
    __tablename__ = "notification_prefs"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    daily_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_time: Mapped[time] = mapped_column(Time, default=time(7, 30))  # local time at the user's city
    transit_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="notification_prefs")


class NotificationLog(Base):
    """One row per user, kind and local date, so a message is never sent twice. Holds no message text."""
    __tablename__ = "notification_log"
    __table_args__ = (UniqueConstraint("user_id", "kind", "local_date", name="uq_notification_once"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # "daily"
    local_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(12))  # sending, sent, failed, no_device
    attempts: Mapped[int] = mapped_column(SmallInteger, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ChatConversation(Base):
    """A chat with the AI guide. Personal data: only its owner can read it, and it is removed with the
    account or with the birth profile it was about."""
    __tablename__ = "chat_conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("birth_profiles.id", ondelete="CASCADE"), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # Older messages are folded into this short summary so the model keeps the thread without an ever-growing prompt.
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summarized_through: Mapped[int | None] = mapped_column(Integer, nullable=True)  # last message id inside the summary
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="conversations")
    profile: Mapped["BirthProfile | None"] = relationship(back_populates="conversations")
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="ChatMessage.created_at, ChatMessage.id")


class ChatUsage(Base):
    """One row per message a person sent to the guide: only who and when, never the text. The daily limit counts these,
    so deleting a chat (or a profile) cannot reset it. Removed with the account."""
    __tablename__ = "chat_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("chat_conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(10))  # user or assistant
    text: Mapped[str] = mapped_column(Text)
    lang: Mapped[str] = mapped_column(String(2))
    source: Mapped[str] = mapped_column(String(12), default="user")  # user, model, safety, fallback
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversation: Mapped[ChatConversation] = relationship(back_populates="messages")


class DailyHoroscope(Base):
    """The written horoscope for one person on one day, in one language. Built the first time it is asked for and
    then kept, so it does not change that day. Personal data: removed with the account or the profile, and included
    in the export."""
    __tablename__ = "daily_horoscopes"
    __table_args__ = (UniqueConstraint("profile_id", "local_date", "lang", name="uq_daily_horoscope_profile_day_lang"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("birth_profiles.id", ondelete="CASCADE"), index=True)
    local_date: Mapped[date] = mapped_column(Date)
    lang: Mapped[str] = mapped_column(String(2))
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), default="draft")  # draft until the wording is reviewed
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="daily_horoscopes")
    profile: Mapped[BirthProfile] = relationship(back_populates="daily_horoscopes")


class LoveReading(Base):
    """The written love and partnership reading for one person, in one language. Built the first time it is asked for
    and then kept (it comes from the birth chart, so it does not change by day). Personal data: removed with the
    account or the profile, and included in the export."""
    __tablename__ = "love_readings"
    __table_args__ = (UniqueConstraint("profile_id", "lang", name="uq_love_reading_profile_lang"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("birth_profiles.id", ondelete="CASCADE"), index=True)
    lang: Mapped[str] = mapped_column(String(2))
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), default="draft")  # draft until the wording is reviewed
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="love_readings")
    profile: Mapped[BirthProfile] = relationship(back_populates="love_readings")


class DailyPlanetCards(Base):
    """The five planet cards of one person's day in one language: for each life area a headline and a one-line
    message written by the model. The planet, sign and house are worked out from the chart each time and not stored.
    Built the first time they are asked for, then kept. Personal data: removed with the account or the profile, or
    when birth details change, and included in the export."""
    __tablename__ = "daily_planet_cards"
    __table_args__ = (UniqueConstraint("profile_id", "local_date", "lang", name="uq_daily_planet_cards_profile_day_lang"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("birth_profiles.id", ondelete="CASCADE"), index=True)
    local_date: Mapped[date] = mapped_column(Date)
    lang: Mapped[str] = mapped_column(String(2))
    texts: Mapped[dict] = mapped_column(JSON)  # {area: {"headline": ..., "message": ...}}
    status: Mapped[str] = mapped_column(String(12), default="draft")
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="planet_cards")
    profile: Mapped[BirthProfile] = relationship(back_populates="planet_cards")


class MatchSummary(Base):
    """The written summary of a compatibility match between two of one user's profiles, in one language. The order
    matters (the first profile is the first column of the match tables). Built the first time it is asked for, then kept.
    Personal data: removed with the account, with either profile, or when either one's birth details change, and
    included in the export."""
    __tablename__ = "match_summaries"
    __table_args__ = (UniqueConstraint("first_profile_id", "second_profile_id", "lang", name="uq_match_summary_pair_lang"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    first_profile_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("birth_profiles.id", ondelete="CASCADE"), index=True)
    second_profile_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("birth_profiles.id", ondelete="CASCADE"), index=True)
    lang: Mapped[str] = mapped_column(String(2))
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), default="draft")
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="match_summaries")


def primary_profile(user: "User") -> "BirthProfile | None":
    """The person's own birth profile: the one labelled "Me", else the oldest. Used for their daily card, their chat
    and their daily notification."""
    return next((p for p in user.profiles if p.label == "Me"), user.profiles[0] if user.profiles else None)
