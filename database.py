import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# Получаем строку подключения из переменной окружения Docker Compose
# Если переменная не установлена (например, при локальном запуске Alembic),
# используется подключение по умолчанию к localhost:5432.
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://user_event:strongpassword@localhost:5432/event_db")

# Создаем асинхронный движок SQLAlchemy
# 'echo=False' - не выводит SQL-запросы в консоль
# 'pool_pre_ping=True' - помогает поддерживать соединение активным
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

# Базовый класс для всех ORM-моделей, от которого наследуются все ваши таблицы
Base = declarative_base()

# Настройка асинхронной фабрики сессий
AsyncSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine, 
    class_=AsyncSession,
    expire_on_commit=False # Важно для асинхронных операций, чтобы объекты оставались доступными после коммита
)

# Функция-зависимость для получения сессии базы данных FastAPI
# Она будет использоваться в маршрутах (endpoints) для выполнения запросов
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            # Обязательное закрытие сессии после завершения работы
            await session.close()

# Функция для создания всех таблиц в БД на основе моделей (используется редко, в основном Alembic)
async def init_db():
    async with engine.begin() as conn:
        # Для начала удаляем все таблицы, чтобы начать с чистого листа (осторожно: удаляет все данные)
        # await conn.run_sync(Base.metadata.drop_all)
        # Создаем все таблицы, определенные в Base.metadata
        await conn.run_sync(Base.metadata.create_all)