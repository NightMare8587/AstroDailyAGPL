from fastapi import FastAPI

from . import __version__
from .api.auth_routes import router as auth_router
from .api.places_routes import router as places_router
from .api.routes import router
from .api.user_routes import router as user_router
from .calc import ephem
from .config import get_settings

settings = get_settings()
ephem.configure(settings.ephemeris_path)

app = FastAPI(title="AstroDaily API", version=__version__)
app.include_router(router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(places_router)
