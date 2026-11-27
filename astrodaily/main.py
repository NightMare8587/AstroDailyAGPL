from fastapi import FastAPI

from . import __version__
from .api.routes import router
from .calc import ephem
from .config import get_settings

settings = get_settings()
ephem.configure(settings.ephemeris_path)

app = FastAPI(title="AstroDaily API", version=__version__)
app.include_router(router)
