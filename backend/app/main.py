from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import auth, budgets, dashboard, export, rules, transactions


def create_app() -> FastAPI:
    app = FastAPI(
        title="Finance Dashboard API",
        version="0.1.0",
        description="Personal finance dashboard backend — CSV import, categorization, budgets, PDF export.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Create tables on startup (simple for SQLite; swap for Alembic if needed).
    Base.metadata.create_all(bind=engine)

    app.include_router(auth.router)
    app.include_router(transactions.router)
    app.include_router(rules.router)
    app.include_router(budgets.router)
    app.include_router(dashboard.router)
    app.include_router(export.router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
