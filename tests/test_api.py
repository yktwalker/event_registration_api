import pytest
from httpx import AsyncClient

# Тест 1: Управление участниками (CRUD + Валидация)
@pytest.mark.asyncio
async def test_participant_crud(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Создание валидного участника
    new_participant = {
        "full_name": "Test Participant",
        "email": "test@example.com",
        "note": "Created via test"
    }
    resp = await client.post("/participants/", json=new_participant, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["full_name"] == new_participant["full_name"]
    assert data["id"] is not None
    participant_id = data["id"]

    # 2. Попытка создать дубликат (должна быть ошибка 400)
    resp_dup = await client.post("/participants/", json=new_participant, headers=headers)
    assert resp_dup.status_code == 400

    # 3. Получение списка участников
    resp_list = await client.get("/participants/", headers=headers)
    assert resp_list.status_code == 200
    participants = resp_list.json()
    assert len(participants) >= 1
    assert any(p["id"] == participant_id for p in participants)

    # 4. Создание участника без обязательного поля (Валидация Pydantic)
    invalid_participant = {"email": "only_email@test.com"}
    resp_inv = await client.post("/participants/", json=invalid_participant, headers=headers)
    assert resp_inv.status_code == 422

# Тест 2: Сценарий работы со справочниками
@pytest.mark.asyncio
async def test_directory_workflow(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Создаем участника для теста
    p_resp = await client.post("/participants/", json={"full_name": "Dir User", "email": "dir@test.com"}, headers=headers)
    assert p_resp.status_code == 200
    p_id = p_resp.json()["id"]

    # 2. Создаем справочник
    dir_data = {"name": "VIP Guests", "description": "Very important"}
    d_resp = await client.post("/directories/", json=dir_data, headers=headers)
    assert d_resp.status_code == 200
    d_id = d_resp.json()["id"]

    # 3. Добавляем участника в справочник
    add_resp = await client.post("/directories/add-member/", json={"directory_id": d_id, "participant_id": p_id}, headers=headers)
    assert add_resp.status_code == 200

    # 4. Проверяем состав справочника
    members_resp = await client.get(f"/directories/{d_id}/members/", headers=headers)
    assert members_resp.status_code == 200
    members = members_resp.json()
    assert len(members) == 1
    assert members[0]["id"] == p_id

    # 5. Удаляем участника из справочника
    del_memb_resp = await client.delete(f"/directories/{d_id}/members/{p_id}", headers=headers)
    assert del_memb_resp.status_code == 204

    # 6. Проверяем, что справочник пуст
    members_resp_empty = await client.get(f"/directories/{d_id}/members/", headers=headers)
    assert len(members_resp_empty.json()) == 0

# Тест 3: Обновление событий и справочников (PUT)
@pytest.mark.asyncio
async def test_update_event_and_directory(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # --- Event Update ---
    # 1. Создаем первое активное событие
    event1_data = {"title": "Event 1", "event_date": "2025-10-01T10:00:00", "registration_active": True}
    e1_resp = await client.post("/events/", json=event1_data, headers=headers)
    assert e1_resp.status_code == 200
    e1_id = e1_resp.json()["id"]

    # 2. Создаем второе неактивное событие
    # (Благодаря исправлению в main.py, это должно пройти успешно даже при активном Event 1)
    event2_data = {"title": "Event 2", "event_date": "2025-10-02T10:00:00", "registration_active": False}
    e2_resp = await client.post("/events/", json=event2_data, headers=headers)
    assert e2_resp.status_code == 200
    e2_id = e2_resp.json()["id"]

    # 3. Пытаемся активировать второе событие через PUT -> Должна быть ошибка 400
    update_fail = await client.put(f"/events/{e2_id}", json={"registration_active": True}, headers=headers)
    assert update_fail.status_code == 400
    assert "активное мероприятие" in update_fail.json()["detail"]

    # 4. Деактивируем первое событие
    update_ok_1 = await client.put(f"/events/{e1_id}", json={"registration_active": False}, headers=headers)
    assert update_ok_1.status_code == 200
    assert update_ok_1.json()["registration_active"] is False

    # 5. Теперь активируем второе событие -> Должно быть успешно
    update_ok_2 = await client.put(f"/events/{e2_id}", json={"registration_active": True, "title": "Updated Event 2"}, headers=headers)
    assert update_ok_2.status_code == 200
    assert update_ok_2.json()["registration_active"] is True
    assert update_ok_2.json()["title"] == "Updated Event 2"

    # --- Directory Update ---
    # 1. Создаем справочник
    dir_resp = await client.post("/directories/", json={"name": "Old Name"}, headers=headers)
    d_id = dir_resp.json()["id"]

    # 2. Обновляем справочник
    dir_update = await client.put(f"/directories/{d_id}", json={"name": "New Name", "description": "Updated desc"}, headers=headers)
    assert dir_update.status_code == 200
    assert dir_update.json()["name"] == "New Name"
    assert dir_update.json()["description"] == "Updated desc"

# Тест 4: Обновление участника (PUT)
@pytest.mark.asyncio
async def test_participant_update(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Создаем участника
    p_data = {"full_name": "Original Name", "email": "orig@test.com", "note": "Note 1"}
    resp = await client.post("/participants/", json=p_data, headers=headers)
    assert resp.status_code == 200
    p_id = resp.json()["id"]

    # 2. Обновляем имя и email
    update_data = {"full_name": "New Name", "email": "new@test.com"}
    resp_upd = await client.put(f"/participants/{p_id}", json=update_data, headers=headers)
    assert resp_upd.status_code == 200
    data = resp_upd.json()
    assert data["full_name"] == "New Name"
    assert data["email"] == "new@test.com"
    assert data["note"] == "Note 1" # Не должно измениться

    # 3. Пытаемся обновить на имя, которое уже есть (конфликт дубликатов)
    # Сначала создадим второго участника
    await client.post("/participants/", json={"full_name": "Another User", "email": "another@test.com", "note": "Note 1"}, headers=headers)
    
    # Пытаемся переименовать первого во второго (должно упасть с 400, так как имя+note совпадут)
    # У первого note="Note 1", у второго note="Note 1" и имя "Another User"
    resp_fail = await client.put(f"/participants/{p_id}", json={"full_name": "Another User"}, headers=headers)
    assert resp_fail.status_code == 400
