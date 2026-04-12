"""Point d'entrée FastAPI — FinanceAI Backend."""
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from database import SessionLocal
from app.scheduler.jobs import start_scheduler, stop_scheduler
from app.api.routes import tasks, files, analysis, notifications, chat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup — les migrations sont gérées par Alembic (alembic upgrade head)
    logger.info("FinanceAI Backend démarrage...")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    db = SessionLocal()
    try:
        start_scheduler(db)
    finally:
        db.close()

    logger.info("FinanceAI Backend prêt.")
    yield

    # Shutdown
    stop_scheduler()
    logger.info("FinanceAI Backend arrêté.")


app = FastAPI(
    title="FinanceAI API",
    description="Backend IA pour la gestion financière automatisée",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(tasks.router)
app.include_router(files.router)
app.include_router(analysis.router)
app.include_router(notifications.router)
app.include_router(chat.router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "FinanceAI Backend",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
