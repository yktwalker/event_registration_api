import pytest
from datetime import datetime, timezone
from sqlalchemy import select
import models

# Вспомогательная фикстура для заголовков
@pytest.fixture
def admin_token_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}

@pytest.mark.asyncio
async def test_active_event_stats(client, admin_token_headers, db_session):
    """
    Тест ендпоинта /events/active/stats
    Используем сохранение ID в переменные, чтобы избежать MissingGreenlet.
    """
    db = db_session 

    # 1. Деактивируем существующие активные ивенты
    stmt = select(models.Event).filter(models.Event.registration_active == True)
    result = await db.execute(stmt)
    active_events = result.scalars().all()
    for e in active_events:
        e.registration_active = False
    await db.commit()

    # Запрос при отсутствии активного мероприятия
    response = await client.get("/events/active/stats", headers=admin_token_headers)
    assert response.status_code == 404

    # 2. Создаем активное мероприятие
    active_event = models.Event(
        title="Stats Test Event",
        event_date=datetime.now(),
        registration_active=True
    )
    db.add(active_event)
    await db.commit()
    await db.refresh(active_event)
    # ВАЖНО: Сохраняем ID сразу, так как следующий commit (при создании участников)
    # сделает объект active_event "expired".
    active_event_id = active_event.id

    # 3. Создаем участников
    p1 = models.Participant(full_name="User One", email="u1@test.com")
    p2 = models.Participant(full_name="User Two", email="u2@test.com")
    db.add_all([p1, p2])
    await db.commit()
    await db.refresh(p1)
    await db.refresh(p2)
    # ВАЖНО: Сохраняем ID участников
    p1_id = p1.id
    p2_id = p2.id

    # Получаем системного пользователя
    stmt_user = select(models.SystemUser).limit(1)
    user_res = await db.execute(stmt_user)
    sys_user = user_res.scalars().first()
    sys_user_id = sys_user.id

    # 4. Регистрации (используем сохраненные ID, а не объекты!)
    reg1 = models.Registration(
        event_id=active_event_id,      # используем переменную
        participant_id=p1_id,          # используем переменную
        registered_by_user_id=sys_user_id
    )
    reg2 = models.Registration(
        event_id=active_event_id,      # используем переменную
        participant_id=p2_id,          # используем переменную
        registered_by_user_id=sys_user_id,
        arrival_time=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    db.add_all([reg1, reg2])
    await db.commit()

    # 5. Проверяем статистику
    response = await client.get("/events/active/stats", headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["event_title"] == "Stats Test Event"
    assert data["total_registrants"] == 2
    assert data["arrived_participants"] == 1


@pytest.mark.asyncio
async def test_download_stats_file(client, admin_token_headers, db_session):
    """
    Тест ендпоинта /events/{event_id}/stats/file
    """
    db = db_session

    # 1. Создаем мероприятие
    event = models.Event(
        title="File Report Event",
        event_date=datetime.now(),
        registration_active=False
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    # Сохраняем ID
    event_id = event.id

    # 2. Подготовка участников
    p1 = models.Participant(full_name="Ivanov Ivan", email="ivan@test.com")
    p2 = models.Participant(full_name="Petrov Petr", email="petr@test.com")
    db.add_all([p1, p2])
    await db.commit()
    await db.refresh(p1)
    await db.refresh(p2)
    # Сохраняем ID
    p1_id = p1.id
    p2_id = p2.id

    stmt_user = select(models.SystemUser).limit(1)
    sys_user = (await db.execute(stmt_user)).scalars().first()
    sys_user_id = sys_user.id

    # 3. Регистрации (используем ID)
    # Ivanov - пришел
    reg1 = models.Registration(
        event_id=event_id,
        participant_id=p1_id,
        registered_by_user_id=sys_user_id,
        arrival_time=datetime.now(timezone.utc).replace(tzinfo=None)
    )
    # Petrov - не пришел
    reg2 = models.Registration(
        event_id=event_id,
        participant_id=p2_id,
        registered_by_user_id=sys_user_id,
        arrival_time=None
    )
    db.add_all([reg1, reg2])
    await db.commit()

    # 4. Запрос файла
    response = await client.get(f"/events/{event_id}/stats/file", headers=admin_token_headers)
    
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "attachment; filename=stats_" in response.headers["content-disposition"]

    content = response.text
    
    # Проверки содержимого
    assert "Статистика по мероприятию: File Report Event" in content
    assert "Ivanov Ivan" in content
    assert "Petrov Petr" in content
    assert "Не пришел" in content # Для Петрова
    
    # Проверка итогов
    assert "ИТОГО ЗАПЛАНИРОВАНО (всего регистраций): 2" in content
    assert "ИТОГО РЕАЛЬНО ПРИШЛО: 1" in content

    # Проверка сортировки (Пришедший Иванов должен быть выше Петрова)
    pos_ivan = content.find("Ivanov Ivan")
    pos_petr = content.find("Petrov Petr")
    assert pos_ivan < pos_petr
