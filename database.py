"""Base de données — SQLAlchemy sync + pg8000 (pure Python, compatible Python 3.14)."""
import ssl
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings


def _build_pg8000_url(raw_url: str) -> tuple[str, dict]:
    """
    Convertit une URL postgresql://... en URL pg8000 + connect_args SSL.
    pg8000 ne supporte pas ?sslmode=require dans l'URL — SSL est passé via connect_args.
    """
    # Nettoyer les params non supportés par pg8000
    url = re.sub(r"postgresql(\+\w+)?://", "postgresql+pg8000://", raw_url)
    url = re.sub(r"\?.*$", "", url)  # retirer les query params

    # Configurer SSL pour NeonDB
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = True
    ssl_context.verify_mode = ssl.CERT_REQUIRED

    connect_args = {"ssl_context": ssl_context}
    return url, connect_args


_db_url, _connect_args = _build_pg8000_url(settings.DATABASE_URL)

engine = create_engine(
    _db_url,
    connect_args=_connect_args,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

Base = declarative_base()


def get_db():
    """Dépendance FastAPI — session sync (FastAPI la lance dans un thread pool)."""
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
