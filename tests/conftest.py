import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 1. Настройка окружения
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "TEST_SECRET"

# 2. Импорты
from database import Base, get_db
from main import app

# --- НАСТРОЙКА ТЕСТОВОЙ БД ---
engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine, 
    class_=AsyncSession,
    expire_on_commit=False
)

@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestingSessionLocal() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
def override_get_db(db_session):
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

@pytest_asyncio.fixture
async def admin_token(client):
    from models import SystemUser, SystemUserRole
    from dependencies import get_password_hash

    async with TestingSessionLocal() as session:
        admin = SystemUser(
            username="admin",
            role=SystemUserRole.ADMIN,
            hashed_password=get_password_hash("admin"),
            full_name="Admin"
        )
        session.add(admin)
        await session.commit()
    
    resp = await client.post("/token", data={"username": "admin", "password": "admin"})
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to get admin token: {resp.text}")
    return resp.json()["access_token"]

@pytest_asyncio.fixture
async def registrar_token_headers(client):
    from models import SystemUser, SystemUserRole
    from dependencies import get_password_hash 

    async with TestingSessionLocal() as session:
        user = SystemUser(
            username="registrar_test",
            role=SystemUserRole.REGISTRAR,
            hashed_password=get_password_hash("regpass"),
            full_name="Registrar Test"
        )
        session.add(user)
        await session.commit()
    
    resp = await client.post("/token", data={"username": "registrar_test", "password": "regpass"})
    if resp.status_code != 200:
         raise RuntimeError(f"Failed to login as registrar: {resp.text}")
         
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture
async def operator_token_headers(client):
    from models import SystemUser, SystemUserRole
    from dependencies import get_password_hash
    
    async with TestingSessionLocal() as session:
        user = SystemUser(
            username="operator_test",
            role=SystemUserRole.OPERATOR,
            hashed_password=get_password_hash("oppass"),
            full_name="Operator Test"
        )
        session.add(user)
        await session.commit()
    
    resp = await client.post("/token", data={"username": "operator_test", "password": "oppass"})
    if resp.status_code != 200:
         raise RuntimeError(f"Failed to login as operator: {resp.text}")

    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
