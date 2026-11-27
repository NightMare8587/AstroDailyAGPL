import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, SmallInteger, String, Time, UniqueConstraint, Uuid,
)
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
    picture_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    language: Mapped[str] = mapped_column(String(2), default="en")  # "en" or "hi"
    # Consent to the privacy policy / data use. Null until the user accepts.
    consent_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(40))
    birth_date: Mapped[date] = mapped_column(Date)
    birth_time: Mapped[time] = mapped_column(Time)
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
