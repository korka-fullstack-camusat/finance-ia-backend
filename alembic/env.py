"""Alembic env — pg8000 (pure Python), compatible Python 3.14."""
import os
import sys
import ssl
import re
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Import Base + tous les modèles pour autogenerate
from database import Base  # noqa: E402
from app.models.task import Task, TaskResult  # noqa: F401
from app.models.file import UploadedFile  # noqa: F401
from app.models.notification import Notification  # noqa: F401

config = context.config

raw_url = os.environ.get("DATABASE_URL", "")
if not raw_url:
    raise RuntimeError("DATABASE_URL non défini dans .env")

# Convertir en URL pg8000 (pure Python, compatible Python 3.14)
pg8000_url = re.sub(r"postgresql(\+\w+)?://", "postgresql+pg8000://", raw_url)
pg8000_url = re.sub(r"\?.*$", "", pg8000_url)

config.set_main_option("sqlalchemy.url", pg8000_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_connect_args():
    ctx = ssl.create_default_context()
    ctx.check_hostname = True
    ctx.verify_mode = ssl.CERT_REQUIRED
    return {"ssl_context": ctx}


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


def run_migrations_online() -> None:
    engine = create_engine(
        pg8000_url,
        connect_args=_get_connect_args(),
        poolclass=pool.NullPool,
    )
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
