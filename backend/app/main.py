from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import engine
from app.routers import agent, auth, chat, dashboard, etl, glucose, health_reports, me, meals, users


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title="MetaboDash API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def startup() -> None:
        Base.metadata.create_all(bind=engine)

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
    app.include_router(users.router, prefix="/api/users", tags=["users"])
    app.include_router(me.router, prefix="/api", tags=["users"])
    app.include_router(glucose.router, prefix="/api/glucose", tags=["glucose"])
    app.include_router(meals.router, prefix="/api/meals", tags=["meals"])
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
    app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
    app.include_router(etl.router, prefix="/api/etl", tags=["etl"])
    app.include_router(health_reports.router, prefix="/api/health-reports", tags=["health-reports"])
    app.include_router(agent.router, prefix="/api/agent", tags=["agent"])

    return app


app = create_app()
