import pytest
import pytest_asyncio
from datetime import datetime
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from models import SystemUser, SystemUserRole, Event, Participant
from dependencies import get_password_hash

# --- Фикстуры для создания пользователей разных ролей ---

@pytest_asyncio.fixture
async def registrar_token(client: AsyncClient, db_session: AsyncSession):
    """Создает пользователя-регистратора и возвращает его токен."""
    user = SystemUser(
        username="registrar",
        role=SystemUserRole.REGISTRAR,
        hashed_password=get_password_hash("registrar"),
        full_name="Reg User"
    )
    db_session.add(user)
    await db_session.commit()
    
    resp = await client.post("/token", data={"username": "registrar", "password": "registrar"})
    assert resp.status_code == 200
    return resp.json()["access_token"]

@pytest_asyncio.fixture
async def operator_token(client: AsyncClient, db_session: AsyncSession):
    """Создает пользователя-оператора и возвращает его токен."""
    user = SystemUser(
        username="operator",
        role=SystemUserRole.OPERATOR,
        hashed_password=get_password_hash("operator"),
        full_name="Op User"
    )
    db_session.add(user)
    await db_session.commit()
    
    resp = await client.post("/token", data={"username": "operator", "password": "operator"})
    assert resp.status_code == 200
    return resp.json()["access_token"]

@pytest_asyncio.fixture
async def setup_event_and_participant(db_session: AsyncSession):
    """Создает тестовое мероприятие и участника."""
    # 1. Создаем мероприятие
    event = Event(
        title="Test Event",
        # ИСПРАВЛЕНИЕ: Передаем объект datetime, а не строку
        event_date=datetime(2025, 12, 31, 12, 0, 0),
        registration_active=True
    )
    db_session.add(event)
    
    # 2. Создаем участника
    participant = Participant(
        full_name="John Doe",
        email="john@example.com",
        note="Test note"
    )
    db_session.add(participant)
    
    await db_session.commit()
    await db_session.refresh(event)
    await db_session.refresh(participant)
    
    return event, participant

# --- ТЕСТЫ ---

@pytest.mark.asyncio
async def test_registration_permissions(
    client: AsyncClient, 
    registrar_token: str, 
    operator_token: str,
    setup_event_and_participant
):
    """
    Проверяем разделение прав:
    - Регистратор НЕ может создавать регистрации (план).
    - Оператор МОЖЕТ создавать регистрации (план).
    """
    event, participant = setup_event_and_participant
    
    # 1. Попытка Регистратора создать регистрацию (должен получить 403)
    headers_reg = {"Authorization": f"Bearer {registrar_token}"}
    resp_fail = await client.post(
        f"/events/{event.id}/register/", 
        json={"participant_ids": [participant.id]}, 
        headers=headers_reg
    )
    assert resp_fail.status_code == 403, "Регистратор не должен иметь прав на создание заявки"

    # 2. Попытка Оператора создать регистрацию (должен получить 200)
    headers_op = {"Authorization": f"Bearer {operator_token}"}
    resp_ok = await client.post(
        f"/events/{event.id}/register/", 
        json={"participant_ids": [participant.id]}, 
        headers=headers_op
    )
    assert resp_ok.status_code == 200, "Оператор должен успешно создать заявку"
    data = resp_ok.json()
    assert len(data) == 1
    assert data[0]["participant_id"] == participant.id
    assert data[0]["arrival_time"] is None  # При создании время прибытия пустое

@pytest.mark.asyncio
async def test_arrival_workflow(
    client: AsyncClient, 
    registrar_token: str, 
    operator_token: str,
    setup_event_and_participant
):
    """
    Проверяем рабочий процесс Регистратора:
    - Простановка времени прибытия (Факт).
    - Снятие времени прибытия (Ошибка).
    """
    event, participant = setup_event_and_participant
    headers_op = {"Authorization": f"Bearer {operator_token}"}
    headers_reg = {"Authorization": f"Bearer {registrar_token}"}

    # 1. Сначала Оператор региструет участника (создает План)
    await client.post(
        f"/events/{event.id}/register/", 
        json={"participant_ids": [participant.id]}, 
        headers=headers_op
    )

    # 2. Регистратор ставит отметку о прибытии (PUT)
    resp_arrive = await client.put(
        f"/events/{event.id}/participants/{participant.id}/arrival",
        headers=headers_reg
    )
    assert resp_arrive.status_code == 200
    data = resp_arrive.json()
    assert data["arrival_time"] is not None
    assert "T" in data["arrival_time"] # Проверка формата времени ISO

    # 3. Проверяем через поиск, что время действительно стоит
    resp_search = await client.get(
        f"/events/{event.id}/registrations/search?query=John",
        headers=headers_reg
    )
    assert resp_search.status_code == 200
    search_data = resp_search.json()
    assert len(search_data) > 0
    assert search_data[0]["arrival_time"] is not None

    # 4. Регистратор ошибочно поставил, нужно снять (DELETE)
    resp_cancel = await client.delete(
        f"/events/{event.id}/participants/{participant.id}/arrival",
        headers=headers_reg
    )
    assert resp_cancel.status_code == 204

    # 5. Проверяем, что время очистилось
    resp_check = await client.get(
        f"/events/{event.id}/registrations/search?query=John",
        headers=headers_reg
    )
    item = resp_check.json()[0]
    assert item["arrival_time"] is None

@pytest.mark.asyncio
async def test_arrival_errors(
    client: AsyncClient, 
    registrar_token: str, 
    setup_event_and_participant
):
    """Проверка ошибок при простановке прибытия."""
    event, participant = setup_event_and_participant
    headers_reg = {"Authorization": f"Bearer {registrar_token}"}

    # 1. Попытка поставить прибытие незарегистрированному участнику (нет в плане)
    # (Мы специально НЕ вызываем /register/ перед этим)
    resp_fail = await client.put(
        f"/events/{event.id}/participants/{participant.id}/arrival",
        headers=headers_reg
    )
    assert resp_fail.status_code == 404
    assert "не зарегистрирован" in resp_fail.json()["detail"]
    