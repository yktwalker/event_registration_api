import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_participant_directories_loading(
    client: AsyncClient,
    admin_token: str
):
    """
    Старый тест: проверяет, что при получении участника (GET /participants/)
    мы видим список справочников, в которых он состоит.
    """
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
    res_list = await client.get("/participants/", headers=headers)
    assert res_list.status_code == 200
    found_p = next((p for p in res_list.json() if p["id"] == p_id), None)
    assert found_p is not None
    
    # Проверяем, что справочник пришел и в списке
    assert len(found_p["directories"]) > 0
    found_dir_list = next((d for d in found_p["directories"] if d["id"] == d_id), None)
    assert found_dir_list is not None
    assert found_dir_list["name"] == "Test Directory Unique"


@pytest.mark.asyncio
async def test_directory_members_pagination(
    client: AsyncClient, 
    admin_token: str
):
    """
    Новый тест: проверяет пагинацию (offset/limit) при получении 
    списка участников КОНКРЕТНОГО справочника.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Создаем справочник для теста пагинации
    d_resp = await client.post("/directories/", json={"name": "Pagination Test"}, headers=headers)
    assert d_resp.status_code == 200
    d_id = d_resp.json()["id"]

    # 2. Создаем и добавляем 5 участников
    # Чтобы порядок был предсказуемым, мы их создаем последовательно
    for i in range(5):
        p_data = {"full_name": f"PageUser {i}", "email": f"page{i}@test.com", "note": "pagination"}
        p_resp = await client.post("/participants/", json=p_data, headers=headers)
        p_id = p_resp.json()["id"]
        await client.post("/directories/add-member/", json={"directory_id": d_id, "participant_id": p_id}, headers=headers)

    # 3. Тест: limit=2, offset=0 (Ожидаем User 0, User 1)
    resp_page1 = await client.get(f"/directories/{d_id}/members/?limit=2&offset=0", headers=headers)
    assert resp_page1.status_code == 200
    data1 = resp_page1.json()
    assert len(data1) == 2
    # Сортировка по умолчанию в БД обычно по ID, так как мы добавляли последовательно, порядок должен сохраниться
    assert data1[0]["full_name"] == "PageUser 0"
    assert data1[1]["full_name"] == "PageUser 1"

    # 4. Тест: limit=2, offset=2 (Ожидаем User 2, User 3)
    resp_page2 = await client.get(f"/directories/{d_id}/members/?limit=2&offset=2", headers=headers)
    assert resp_page2.status_code == 200
    data2 = resp_page2.json()
    assert len(data2) == 2
    assert data2[0]["full_name"] == "PageUser 2"
    assert data2[1]["full_name"] == "PageUser 3"

    # 5. Тест: limit=2, offset=4 (Ожидаем User 4)
    resp_page3 = await client.get(f"/directories/{d_id}/members/?limit=2&offset=4", headers=headers)
    assert resp_page3.status_code == 200
    data3 = resp_page3.json()
    assert len(data3) == 1
    assert data3[0]["full_name"] == "PageUser 4"
    
    # 6. Тест: лимит больше 500 (проверка снятия ограничения)
    resp_big = await client.get(f"/directories/{d_id}/members/?limit=1000", headers=headers)
    assert resp_big.status_code == 200
    # Должен вернуть всех 5, не обрезая (хотя тут всего 5, но главное, что ошибки 422 нет)
    assert len(resp_big.json()) == 5
