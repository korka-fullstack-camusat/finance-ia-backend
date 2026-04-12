"""Base de données asynchrone — SQLAlchemy + asyncpg + NeonDB PostgreSQL."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

# Convertir l'URL PostgreSQL en URL asyncpg
# postgresql://... → postgresql+asyncpg://...
def _make_async_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url

ASYNC_DATABASE_URL = _make_async_url(settings.DATABASE_URL)

# Moteur asynchrone optimisé pour NeonDB (serverless pooler)
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,       # vérifie la connexion avant utilisation
    pool_recycle=300,         # recycle les connexions toutes les 5 min
    echo=False,               # passer à True pour debug SQL
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,   # évite les lazy loads après commit
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncSession:
    """Dépendance FastAPI : session DB asynchrone."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
