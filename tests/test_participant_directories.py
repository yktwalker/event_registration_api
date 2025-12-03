import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_participant_directories_loading(
    client: AsyncClient,
    admin_token: str
):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Создаем участника
    p_data = {
        "full_name": "Directory Test User", 
        "email": "dir_test@example.com",
        "note": "test"
    }
    res_p = await client.post("/participants/", json=p_data, headers=headers)
    assert res_p.status_code == 200
    p_id = res_p.json()["id"]

    # 2. Создаем справочник
    d_data = {"name": "Test Directory Unique", "description": "desc"}
    res_d = await client.post("/directories/", json=d_data, headers=headers)
    assert res_d.status_code == 200
    d_id = res_d.json()["id"]

    # 3. Добавляем участника в справочник
    link_data = {"participant_id": p_id, "directory_id": d_id}
    res_link = await client.post("/directories/add-member/", json=link_data, headers=headers)
    assert res_link.status_code == 200

    # 4. ПРОВЕРКА: GET /{id} (Детальный просмотр)
    res_get = await client.get(f"/participants/{p_id}", headers=headers)
    assert res_get.status_code == 200
    data = res_get.json()
    
    assert "directories" in data
    found_dir = next((d for d in data["directories"] if d["id"] == d_id), None)
    assert found_dir is not None
    assert found_dir["name"] == "Test Directory Unique"

    # 5. ПРОВЕРКА: GET /participants/ (Общий список)
    # ТЕПЕРЬ ЗДЕСЬ ТОЖЕ ДОЛЖНЫ БЫТЬ ДАННЫЕ (мы это включили в main.py)
    res_list = await client.get("/participants/", headers=headers)
    assert res_list.status_code == 200
    found_p = next((p for p in res_list.json() if p["id"] == p_id), None)
    assert found_p is not None
    
    # Проверяем, что справочник пришел и в списке
    assert len(found_p["directories"]) > 0
    found_dir_list = next((d for d in found_p["directories"] if d["id"] == d_id), None)
    assert found_dir_list is not None
    assert found_dir_list["name"] == "Test Directory Unique"
