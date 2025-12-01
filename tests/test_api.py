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
    # full_name обязателен в Pydantic (если вы не меняли схему на Optional)
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
