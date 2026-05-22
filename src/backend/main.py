from __future__ import annotations

from fastapi import FastAPI

from src.shared.config.settings import get_settings
from src.backend.startup import attach_startup

# register API routers
from src.backend.api.catalog import router as catalog_router
from src.backend.api.enquiries import router as enquiries_router
from src.backend.api.chat import router as chat_router
from src.backend.api.recommendations import router as recommendations_router
from src.backend.api.finance import router as finance_router
from src.backend.api.shortlist import router as shortlist_router
from src.backend.api.comparisons import router as comparisons_router
from src.backend.api.analytics import router as analytics_router

app = FastAPI(title="AI Car Buying Assistant Backend", version="0.1.0")

# attach startup handlers (load catalog, optional vectorstore)
attach_startup(app)

# include routers
app.include_router(catalog_router)
app.include_router(enquiries_router)
app.include_router(chat_router)
app.include_router(recommendations_router)
app.include_router(finance_router)
app.include_router(shortlist_router)
app.include_router(comparisons_router)
app.include_router(analytics_router)


@app.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "env": "docker-compose",
        "fastapi_host": settings.fastapi_host,
        "fastapi_port": str(settings.fastapi_port),
    }
