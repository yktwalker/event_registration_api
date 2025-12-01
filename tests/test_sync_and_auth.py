import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_auth_permissions(client: AsyncClient, admin_token: str):
    # 1. Создаем обычного регистратора (не админа)
    reg_data = {
        "username": "registrar1", 
        "password": "password123", 
        "full_name": "Reg User",
        "role": "Registrar"
    }
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    
    # Создаем пользователя через админа
    resp = await client.post("/system-users/", json=reg_data, headers=headers_admin)
    assert resp.status_code == 200

    # Логинимся как регистратор
    login_resp = await client.post("/token", data={"username": "registrar1", "password": "password123"})
    assert login_resp.status_code == 200
    registrar_token = login_resp.json()["access_token"]
    headers_reg = {"Authorization": f"Bearer {registrar_token}"}

    # 2. Регистратор пытается удалить событие (должен получить 403)
    # Сначала создадим событие админом
    evt_resp = await client.post("/events/", json={"title": "Protected Event", "event_date": "2025-05-05T10:00:00"}, headers=headers_admin)
    evt_id = evt_resp.json()["id"]
    
    del_resp = await client.delete(f"/events/{evt_id}", headers=headers_reg)
    assert del_resp.status_code == 403  # Forbidden

@pytest.mark.asyncio
async def test_sync_logic(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 1. Подготовка: Создаем событие и 2 участников
    evt = await client.post("/events/", json={"title": "Sync Event", "event_date": "2025-06-01T12:00:00"}, headers=headers)
    event_id = evt.json()["id"]
    
    p1 = await client.post("/participants/", json={"full_name": "P1", "email": "p1@test.com"}, headers=headers)
    p2 = await client.post("/participants/", json={"full_name": "P2", "email": "p2@test.com"}, headers=headers)
    p1_id = p1.json()["id"]
    p2_id = p2.json()["id"]

    # 2. Регистрируем P1 сейчас
    await client.post(f"/events/{event_id}/register/", json={"participant_ids": [p1_id]}, headers=headers)
    
    # 3. Запрашиваем синхронизацию (как будто мы только что подключились)
    # Мы ничего не знаем (known_ids пуст), last_sync давно
    sync_req = {
        "last_sync_time": "2020-01-01T00:00:00",
        "known_registration_ids": []
    }
    sync_resp = await client.post(f"/events/{event_id}/sync/", json=sync_req, headers=headers)
    assert sync_resp.status_code == 200
    data = sync_resp.json()
    
    # Должны получить 1 регистрацию (P1)
    assert len(data["new_registrations"]) == 1
    assert data["new_registrations"][0]["participant_id"] == p1_id
    
    # Запоминаем ID регистрации P1
    reg_id_p1 = data["new_registrations"][0]["id"]

    # 4. Регистрируем P2
    await client.post(f"/events/{event_id}/register/", json={"participant_ids": [p2_id]}, headers=headers)

    # 5. Повторная синхронизация
    # Теперь мы знаем про P1 (отправляем его ID в known_registration_ids)
    sync_req_2 = {
        "last_sync_time": "2020-01-01T00:00:00", # Время можно не менять для теста логики исключения ID
        "known_registration_ids": [reg_id_p1]
    }
    sync_resp_2 = await client.post(f"/events/{event_id}/sync/", json=sync_req_2, headers=headers)
    data_2 = sync_resp_2.json()
    
    # Должны получить ТОЛЬКО P2 (так как P1 мы исключили)
    assert len(data_2["new_registrations"]) == 1
    assert data_2["new_registrations"][0]["participant_id"] == p2_id
