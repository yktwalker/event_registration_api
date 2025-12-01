import asyncio
from datetime import datetime  # <--- ВАЖНО: импортируем datetime
from fastapi.testclient import TestClient
from main import app
from database import get_db, Base
from tests.conftest import TestingSessionLocal, engine
from models import SystemUser, Event

# Функция-заглушка для получения сессии
async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

def test_websocket_broadcast_scenario():
    """
    Проверка WebSocket уведомлений.
    """
    
    # 1. Переопределяем зависимость БД глобально для этого теста
    app.dependency_overrides[get_db] = override_get_db
    
    # 2. Функция инициализации данных
    async def init_test_data():
        # Создаем таблицы
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        async with TestingSessionLocal() as session:
            # Создаем ивент
            # ИСПРАВЛЕНИЕ: Передаем datetime объект, а не строку!
            evt = Event(
                title="WS Event", 
                event_date=datetime(2025, 1, 1, 12, 0, 0), # <--- БЫЛА ОШИБКА ТУТ
                registration_active=True
            )
            session.add(evt)
            
            # Создаем админа
            admin = SystemUser(
                username="admin_ws", 
                role="Admin", 
                hashed_password="hash", 
                full_name="WS Admin"
            )
            session.add(admin)
            await session.commit()
            
            # Рефрешим, чтобы получить ID
            await session.refresh(evt)
            await session.refresh(admin)
            return evt.id, admin.id

    # Запускаем подготовку данных через asyncio.run
    event_id, admin_id = asyncio.run(init_test_data())

    # 3. Мокаем проверку прав (Auth)
    from main import get_current_registrar_or_admin, get_current_admin
    
    async def mock_get_user():
        return SystemUser(id=admin_id, username="admin_ws", role="Admin")
        
    app.dependency_overrides[get_current_registrar_or_admin] = mock_get_user
    app.dependency_overrides[get_current_admin] = mock_get_user

    try:
        # 4. Запускаем TestClient (он синхронный)
        with TestClient(app) as client:
            
            # Создаем участника через API
            p_resp = client.post("/participants/", json={
                "full_name": "Socket User", "email": "socket@test.com"
            })
            assert p_resp.status_code == 200
            p_id = p_resp.json()["id"]

            # 5. Подключаемся к WebSocket
            # Указываем полный путь ws://... хотя TestClient часто понимает и относительный
            with client.websocket_connect(f"/ws/events/{event_id}") as websocket:
                
                # 6. Выполняем регистрацию (триггер уведомления)
                reg_resp = client.post(
                    f"/events/{event_id}/register/",
                    json={"participant_ids": [p_id]}
                )
                assert reg_resp.status_code == 200
                
                # 7. Читаем сообщение из сокета
                data = websocket.receive_json()
                
                # Проверки
                assert data["type"] == "new_registrations"
                assert p_id in data["participant_ids"]
                
    finally:
        # Очистка зависимостей
        app.dependency_overrides = {}
