from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# PostgreSQL : pas de check_same_thread, pool adapté à NeonDB (serverless)
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # vérifie la connexion avant utilisation
    pool_recycle=300,         # recycle les connexions toutes les 5 min
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
