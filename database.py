import os
from datetime import datetime, timedelta
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.future import select
from passlib.context import CryptContext

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./sql_app.db",
)

IS_SQLITE = DATABASE_URL.startswith("sqlite")

Base = declarative_base()

engine_config: dict = {}
if IS_SQLITE:
    engine_config["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    **engine_config,
)

AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


async def init_db(db: AsyncSession) -> None:
    import models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    stmt_admin = select(models.SystemUser).filter(models.SystemUser.role == "Admin")
    result_admin = await db.execute(stmt_admin)
    existing_admin = result_admin.scalars().first()

    if not existing_admin:
        admin_username = os.getenv("ADMIN_USERNAME")
        admin_password = os.getenv("ADMIN_PASSWORD")
        admin_full_name = os.getenv("ADMIN_FULL_NAME", "Initial Admin")

        if admin_username and admin_password:
            print(f"Создаём первого администратора из ENV: {admin_username}")
            admin = models.SystemUser(
                username=admin_username,
                role="Admin",
                full_name=admin_full_name,
                hashed_password=get_password_hash(admin_password),
            )
            db.add(admin)
            await db.commit()
        else:
            print("ВНИМАНИЕ: ADMIN_USERNAME/ADMIN_PASSWORD не заданы, админ не создан.")

    seed_demo = os.getenv("SEED_DEMO_DATA", "false").lower() == "true"
    if not seed_demo:
        return

    events_exist = await db.execute(models.Event.__table__.select().limit(1))
    if events_exist.first():
        print("Демо-данные уже существуют. Пропускаем сидирование.")
        return

    print("Создание демо-данных (Events, Participants)...")

    event1 = models.Event(
        title="Ежегодная конференция IT-безопасности",
        event_date=datetime.now() + timedelta(days=30),
        registration_active=True,
        max_participants=500,
    )

    event2 = models.Event(
        title="Web-Development Workshop",
        event_date=datetime.now() + timedelta(days=60),
        registration_active=False,
        max_participants=100,
    )

    db.add_all([event1, event2])
    await db.flush()

    participant1 = models.Participant(
        event_id=event1.id,
        full_name="Иванов Иван Иванович",
        email="ivan@example.com",
        phone="+79001234567",
        note="Сотрудник отдела А",
    )

    participant2 = models.Participant(
        event_id=event1.id,
        full_name="Петрова Анна Сергеевна",
        email="anna@example.com",
        phone="+79007654321",
        note="Гость",
    )

    db.add_all([participant1, participant2])
    await db.commit()
    print("Сидирование демо-данных завершено.")
