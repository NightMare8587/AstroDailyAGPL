import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from astrodaily.calc import ephem
from astrodaily.config import get_settings


@pytest.fixture(autouse=True, scope="session")
def _configure_ephemeris():
    ephem.configure(None)


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    from astrodaily import ratelimit
    ratelimit.reset()
    yield
    ratelimit.reset()


def _backends():
    params = ["sqlite"]
    if os.environ.get("TEST_DATABASE_URL"):
        params.append("postgres")
    return params


@pytest.fixture(params=_backends())
def engine(request):
    """SQLite in memory always; real Postgres (via the Alembic migrations) when TEST_DATABASE_URL is set."""
    from astrodaily.db import Base, normalize_database_url
    from astrodaily import models  # noqa: F401

    if request.param == "sqlite":
        eng = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
        Base.metadata.create_all(eng)
        yield eng
        eng.dispose()
        return

    url = os.environ["TEST_DATABASE_URL"]
    from alembic import command
    from alembic.config import Config

    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    try:
        command.upgrade(Config("alembic.ini"), "head")
    finally:
        if old is None:
            os.environ.pop("DATABASE_URL")
        else:
            os.environ["DATABASE_URL"] = old
        get_settings.cache_clear()
    eng = create_engine(normalize_database_url(url))
    with eng.begin() as conn:
        conn.execute(text("TRUNCATE users, places CASCADE"))
    yield eng
    eng.dispose()


@pytest.fixture
def client(engine):
    from fastapi.testclient import TestClient

    from astrodaily.api.auth_routes import get_google_verifier
    from astrodaily.auth.google import GoogleIdentity
    from astrodaily.db import get_db, get_optional_db
    from astrodaily.main import app

    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    def fake_verifier():
        def verify(token: str) -> GoogleIdentity:
            from fastapi import HTTPException
            if not token.startswith("good-"):
                raise HTTPException(status_code=401, detail="Invalid Google token")
            sub = token[len("good-"):]
            return GoogleIdentity(sub=sub, email=f"{sub}@example.com", email_verified=True,
                                  name=f"User {sub}", picture=None)
        return verify

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_optional_db] = override_db
    app.dependency_overrides[get_google_verifier] = fake_verifier
    with TestClient(app) as c:
        c.session_factory = factory
        yield c
    app.dependency_overrides.clear()
