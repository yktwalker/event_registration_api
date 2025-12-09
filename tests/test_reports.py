import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from models import Event, Directory, Participant, DirectoryMembership, Registration, SystemUser
from datetime import datetime

@pytest.mark.asyncio
async def test_event_report_generation(
    client: AsyncClient,
    db_session: AsyncSession,
    operator_token_headers: dict,
    registrar_token_headers: dict,
):
    # 1. Подготовка данных (Setup)
    
    # Создаем мероприятие
    event = Event(title="Report Test Event", event_date=datetime.now(), registration_active=True)
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)

    # Создаем справочник "VIP Делегаты"
    directory = Directory(name="VIP Делегаты")
    db_session.add(directory)
    await db_session.commit()
    await db_session.refresh(directory)

    # Создаем двух участников
    p1 = Participant(full_name="User One", email="u1@test.com")
    p2 = Participant(full_name="User Two", email="u2@test.com")
    db_session.add_all([p1, p2])
    await db_session.commit()
    await db_session.refresh(p1)
    await db_session.refresh(p2)

    # Добавляем обоих в справочник
    m1 = DirectoryMembership(directory_id=directory.id, participant_id=p1.id)
    m2 = DirectoryMembership(directory_id=directory.id, participant_id=p2.id)
    db_session.add_all([m1, m2])
    
    # Создаем админа для регистрации (чтобы не гадать с ID)
    admin = SystemUser(
        username="report_admin",
        role="Admin",
        hashed_password="hash",
        full_name="Report Admin"
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)

    # Регистрируем обоих на мероприятие
    reg1 = Registration(
        event_id=event.id, 
        participant_id=p1.id, 
        registered_by_user_id=admin.id, 
        arrival_time=datetime.now() # Пришел
    )
    reg2 = Registration(
        event_id=event.id, 
        participant_id=p2.id, 
        registered_by_user_id=admin.id, 
        arrival_time=None # Не пришел
    )
    db_session.add_all([reg1, reg2])
    await db_session.commit()

    # 2. Тестирование (Execution)
    
    # Пытаемся получить отчет как Регистратор (у него есть права)
    response = await client.get(
        f"/events/{event.id}/report",
        headers=registrar_token_headers
    )

    # 3. Проверка (Assertions)

    # Проверяем статус код
    assert response.status_code == 200
    
    # Проверяем, что вернулся HTML
    assert "text/html" in response.headers["content-type"]
    
    html_content = response.text

    # Проверяем наличие ключевых данных в HTML
    assert "VIP Делегаты" in html_content
    assert "Report Test Event" in html_content
    
    # Проверяем логику подсчета:
    # Запланировано: 2
    # Пришло: 1
    # Процент: 50.0%
    assert "<td>2</td>" in html_content  # Колонка Planned
    assert "<td>1</td>" in html_content  # Колонка Actual
    assert "50.0%" in html_content       # Процент явки

@pytest.mark.asyncio
async def test_report_404_if_event_not_found(
    client: AsyncClient,
    registrar_token_headers: dict,
):
    response = await client.get(
        "/events/999999/report",
        headers=registrar_token_headers
    )
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_report_unauthorized(
    client: AsyncClient,
):
    # Без токена
    response = await client.get("/events/1/report")
    assert response.status_code == 401
