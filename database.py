import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timedelta
from typing import AsyncGenerator
from passlib.context import CryptContext  # Для хеширования при сидировании

# --- КОНФИГУРАЦИЯ БАЗЫ ДАННЫХ ---
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./sql_app.db"
)

IS_SQLITE = DATABASE_URL.startswith("sqlite")

Base = declarative_base()

engine_config = {}
if IS_SQLITE:
    engine_config["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    **engine_config
)

AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Генератор, предоставляющий асинхронную сессию базы данных."""
    async with AsyncSessionLocal() as session:
        yield session

# Контекст для хеширования (используется только при init_db)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

# --- ФУНКЦИЯ ИНИЦИАЛИЗАЦИИ И СИДИРОВАНИЯ ---
async def init_db(db: AsyncSession):
    """
    Создает таблицы и заполняет их тестовыми данными (seed-данные).
    """
    import models

    # 1. Создание таблиц
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Проверка, существуют ли системные пользователи
    existing_users = await db.execute(models.SystemUser.__table__.select())
    if existing_users.first():
        print("Системные пользователи уже существуют. Пропускаем сидирование.")
        return

    print("Создание начальных данных с хешированными паролями...")

    # Пароли совпадают с логинами для теста
    admin_hash = get_password_hash("admin_user")
    registrar_hash = get_password_hash("registrar_user")

    user_admin = models.SystemUser(
        username="admin_user",
        role="Admin",
        full_name="Super Admin",
        hashed_password=admin_hash
    )
    user_registrar = models.SystemUser(
        username="registrar_user",
        role="Registrar",
        full_name="Staff Registrar",
        hashed_password=registrar_hash
    )

    # Тестовые события
    event1 = models.Event(
        title="Ежегодная конференция IT-безопасности",
        event_date=datetime.now() + timedelta(days=30),
        registration_active=True,
        max_participants=500
    )

    event2 = models.Event(
        title="Web-Development Workshop",
        event_date=datetime.now() + timedelta(days=60),
        registration_active=False,
        max_participants=100
    )

    db.add_all([user_admin, user_registrar, event1, event2])
    await db.flush()

    # Тестовые участники
    participant1 = models.Participant(
        event_id=event1.id,
        full_name="Иванов Иван Иванович",
        email="ivan@example.com",
        phone="+79001234567",
        note="Сотрудник отдела А"
    )

    participant2 = models.Participant(
        event_id=event1.id,
        full_name="Петрова Анна Сергеевна",
        email="anna@example.com",
        phone="+79007654321",
        note="Гость"
    )

    db.add_all([participant1, participant2])
    await db.commit()
    print("Сидирование завершено.")
