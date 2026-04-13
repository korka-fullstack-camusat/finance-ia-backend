"""FinanceAI Backend — FastAPI + pg8000 + Python 3.14 compatible."""
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.scheduler.jobs import start_scheduler, stop_scheduler
from app.api.routes import tasks, files, analysis, notifications, chat

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FinanceAI Backend démarrage...")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    start_scheduler()  # seed tâches + démarre APScheduler
    logger.info("FinanceAI Backend prêt ✅")
    yield
    stop_scheduler()
    logger.info("FinanceAI Backend arrêté.")


app = FastAPI(
    title="FinanceAI API",
    description="Backend IA pour la gestion financière — Python 3.14 + pg8000",
    version="2.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        "version": "2.1.0",
        "python_compat": "3.14+",
        "db_driver": "pg8000 (pure Python)",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, workers=1)
