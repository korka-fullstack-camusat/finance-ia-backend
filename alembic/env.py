"""Alembic env — async SQLAlchemy + asyncpg + NeonDB."""
import os
import sys
import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool
from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Import Base + tous les modèles (pour autogenerate)
from database import Base  # noqa: E402
from app.models.task import Task, TaskResult  # noqa: F401
from app.models.file import UploadedFile  # noqa: F401
from app.models.notification import Notification  # noqa: F401

config = context.config

# Construire l'URL async (postgresql+asyncpg://)
raw_url = os.environ.get("DATABASE_URL", "")
if not raw_url:
    raise RuntimeError("DATABASE_URL non défini dans .env")

async_url = (
    raw_url
    .replace("postgresql://", "postgresql+asyncpg://", 1)
    .replace("postgres://", "postgresql+asyncpg://", 1)
)
config.set_main_option("sqlalchemy.url", async_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(async_url, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
