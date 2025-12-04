import pytest
from datetime import datetime, timedelta, UTC

from models import Event, Participant, Registration, SystemUser


async def create_test_data(session, event_id, admin_id):
    """Создаем участников и регистрации для проверки поиска."""
    participants = [
        Participant(full_name="Anna Karenina", email="anna@test.com", note="Vip"),
        Participant(full_name="Boris Godunov", email="boris@test.com", note="Regular"),
        Participant(full_name="Cecil Palmer", email="cecil@test.com", note="Guest"),
        Participant(full_name="Dmitry Donskoy", email="dmitry@test.com", note="Hero"),
    ]
    session.add_all(participants)
    await session.commit()
    for p in participants:
        await session.refresh(p)

    # Anna: прибыла 10 минут назад
    reg1 = Registration(
        event_id=event_id,
        participant_id=participants[0].id,
        registered_by_user_id=admin_id,
        arrival_time=datetime.now(UTC) - timedelta(minutes=10),
    )
    # Boris: прибыл 1 минуту назад (самый свежий)
    reg2 = Registration(
        event_id=event_id,
        participant_id=participants[1].id,
        registered_by_user_id=admin_id,
        arrival_time=datetime.now(UTC) - timedelta(minutes=1),
    )
    # Cecil: не прибыл
    reg3 = Registration(
        event_id=event_id,
        participant_id=participants[2].id,
        registered_by_user_id=admin_id,
        arrival_time=None,
    )
    # Dmitry: не регистрируем

    session.add_all([reg1, reg2, reg3])
    await session.commit()
    return participants


@pytest.mark.asyncio
async def test_search_registrations_endpoint(client, admin_token, db_session):
    from sqlalchemy import select

    # 1. Находим админа и сразу сохраняем его ID
    result = await db_session.execute(
        select(SystemUser).filter_by(username="admin")
    )
    admin = result.scalars().first()
    admin_id = admin.id  # сохраняем до любых commit()

    # 2. Создаем событие и тоже сразу сохраняем его ID
    event = Event(
        title="Search Test Event",
        event_date=datetime.now(UTC) + timedelta(days=1),
        registration_active=True,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    event_id = event.id  # сохраняем ID здесь, до create_test_data (которая делает commit)

    # 3. Наполняем тестовыми данными
    await create_test_data(db_session, event_id, admin_id)

    headers = {"Authorization": f"Bearer {admin_token}"}
    base_url = f"/events/{event_id}/registrations/search"

    # --- ТЕСТ 1: простой поиск по имени ---
    resp = await client.get(f"{base_url}?query=Anna", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["full_name"] == "Anna Karenina"

    # --- ТЕСТ 2: фильтр только прибывшие ---
    resp = await client.get(f"{base_url}?filter_arrived=true", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    names = [p["full_name"] for p in data]
    assert "Anna Karenina" in names
    assert "Boris Godunov" in names
    assert "Cecil Palmer" not in names

    # --- ТЕСТ 3: сортировка по убыванию arrival_time ---
    resp = await client.get(
        f"{base_url}?sort_by=arrival_time_desc", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert [p["full_name"] for p in data] == [
        "Boris Godunov",
        "Anna Karenina",
        "Cecil Palmer",
    ]

    # --- ТЕСТ 4: пагинация + сортировка по алфавиту ---
    resp1 = await client.get(
        f"{base_url}?page=1&limit=1&sort_by=alphabet", headers=headers
    )
    resp2 = await client.get(
        f"{base_url}?page=2&limit=1&sort_by=alphabet", headers=headers
    )
    data1 = resp1.json()
    data2 = resp2.json()
    assert len(data1) == 1
    assert len(data2) == 1
    assert data1[0]["full_name"] == "Anna Karenina"
    assert data2[0]["full_name"] == "Boris Godunov"

    # --- ТЕСТ 5: поиск несуществующего ---
    resp = await client.get(f"{base_url}?query=NonExistent", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []
