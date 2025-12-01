import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 1. ЖЕСТКО ЗАДАЕМ URL ПЕРЕД ИМПОРТОМ APP
# Это предотвратит попытки подключения к Postgres/asyncpg
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "TEST_SECRET"

from main import app, get_db
from database import Base

# --- НАСТРОЙКА ТЕСТОВОЙ БД ---
# Используем StaticPool, чтобы БД жила в памяти между запросами одного теста
engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)

@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Создает таблицы перед тестом и удаляет после"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    # Очистка после теста не обязательна для :memory: с StaticPool, 
    # но полезна для чистоты, если пул переиспользуется.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
def override_get_db(db_session):
    """Фикстура для подмены зависимости БД"""
    async def _override_get_db():
        async with TestingSessionLocal() as session:
            yield session
    
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()

@pytest_asyncio.fixture(scope="function")
async def client(override_get_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

# Фикстура токена (если нужна для других тестов)
@pytest_asyncio.fixture
async def admin_token(client):
    from models import SystemUser
    from database import get_password_hash
    
    async with TestingSessionLocal() as session:
        admin = SystemUser(
            username="admin",
            role="Admin",
            hashed_password=get_password_hash("admin"),
            full_name="Admin"
        )
        session.add(admin)
        await session.commit()
    
    resp = await client.post("/token", data={"username": "admin", "password": "admin"})
    return resp.json()["access_token"]
