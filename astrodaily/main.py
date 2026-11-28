from fastapi import FastAPI

from . import __version__
from .api.auth_routes import router as auth_router
from .api.billing_routes import router as billing_router
from .api.chat_routes import router as chat_router
from .api.daily_text_routes import router as daily_text_router
from .api.chart_kind_routes import router as chart_kind_router
from .api.love_routes import router as love_router
from .api.match_routes import router as match_router
from .api.planet_card_routes import router as planet_card_router
from .api.widget_routes import card_router as widget_card_router, token_router as widget_token_router
from .api.horoscope_routes import feedback_router, me_router as horoscope_me_router
from .api.horoscope_routes import profile_router as horoscope_profile_router
from .api.horoscope_routes import router as horoscope_router
from .api.kundli_routes import router as kundli_router
from .api.legal_routes import router as legal_router
from .api.moonsign_routes import router as moonsign_router
from .api.notification_routes import router as notification_router
from .api.places_routes import router as places_router
from .api.profile_routes import export_router, router as profile_router
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
app.include_router(export_router)
app.include_router(notification_router)
app.include_router(chat_router)
app.include_router(billing_router)
app.include_router(places_router)
app.include_router(kundli_router)
app.include_router(legal_router)
app.include_router(moonsign_router)
app.include_router(profile_router)
app.include_router(horoscope_router)
app.include_router(feedback_router)
app.include_router(horoscope_profile_router)
app.include_router(daily_text_router)
app.include_router(chart_kind_router)
app.include_router(love_router)
app.include_router(match_router)
app.include_router(planet_card_router)
app.include_router(widget_token_router)
app.include_router(widget_card_router)
app.include_router(horoscope_me_router)
