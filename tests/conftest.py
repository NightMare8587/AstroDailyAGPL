import pytest

from astrodaily.calc import ephem


@pytest.fixture(autouse=True, scope="session")
def _configure_ephemeris():
    ephem.configure(None)
