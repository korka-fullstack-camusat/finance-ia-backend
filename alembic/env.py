"""Alembic environment — FinanceAI.

Ce fichier configure Alembic pour :
- Lire DATABASE_URL depuis les variables d'environnement (.env)
- Détecter automatiquement tous les modèles SQLAlchemy
- Générer les migrations avec `alembic revision --autogenerate -m "description"`
- Appliquer les migrations avec `alembic upgrade head`
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Ajouter le répertoire racine au path Python
# pour que les imports (database, app.models, app.config) fonctionnent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Charger les variables d'environnement depuis .env
from dotenv import load_dotenv
load_dotenv()

# Import de Base et de TOUS les modèles
# (nécessaire pour que autogenerate détecte les tables)
from database import Base  # noqa: E402
from app.models.task import Task, TaskResult  # noqa: E402, F401
from app.models.file import UploadedFile  # noqa: E402, F401
from app.models.notification import Notification  # noqa: E402, F401

# Lire la config Alembic (alembic.ini)
config = context.config

# Injecter DATABASE_URL depuis l'environnement
database_url = os.environ.get("DATABASE_URL", "")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL non défini. "
        "Créez un fichier .env avec DATABASE_URL=postgresql://..."
    )

config.set_main_option("sqlalchemy.url", database_url)

# Config logging depuis alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata cible pour l'autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Mode offline : génère le SQL sans connexion DB."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Mode online : se connecte à la DB et applique les migrations."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # NullPool recommandé pour NeonDB serverless
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,           # détecte les changements de type
            compare_server_default=True, # détecte les changements de valeur par défaut
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
