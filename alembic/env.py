"""
Alembic configuration for handling database migrations.
"""

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

# Add the project root to the Python path so we can import app.db.models.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv()

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.database import Base
import app.db.models  # Make sure all models are imported for autogenerate.

config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

MIGRATION_URL = os.getenv("DATABASE_MIGRATION_URL")
if not MIGRATION_URL:
    raise RuntimeError("DATABASE_MIGRATION_URL is not set in .env")

if "+asyncpg" not in MIGRATION_URL and "+psycopg2" not in MIGRATION_URL:
    MIGRATION_URL = MIGRATION_URL.replace("postgresql://", "postgresql+asyncpg://")


def run_migrations_offline() -> None:
    """Run migrations offline (generates SQL script)."""
    context.configure(
        url=MIGRATION_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(MIGRATION_URL, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()