import asyncio
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine # <-- ИМПОРТ: Для асинхронного движка

from alembic import context

# --- ДОБАВЛЕННЫЕ ИМПОРТЫ ДЛЯ АВТОГЕНЕРАЦИИ ---
import sys
import os
# Добавляем корневую директорию проекта в PATH для импорта моделей
sys.path.insert(0, os.path.abspath(".")) 

from database import Base # Импорт из нашего database.py
from models import * # Импорт всех наших ORM-моделей
# ---------------------------------------------

# this is the Alembic Config object, which provides
# access to the values within the .ini file in this directory.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata # <-- Указываем нашу Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None: # <-- ИЗМЕНЕНИЕ: Делаем функцию асинхронной
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = AsyncEngine( # <-- ИЗМЕНЕНИЕ: Используем AsyncEngine
        engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        # <-- ИЗМЕНЕНИЕ: Используем connection.run_sync для выполнения синхронного кода миграций
        await connection.run_sync(do_run_migrations) 

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # <-- ИЗМЕНЕНИЕ: Запускаем асинхронную функцию с помощью asyncio.run
    asyncio.run(run_migrations_online())