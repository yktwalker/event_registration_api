import pytest
from main import app
from fastapi.testclient import TestClient

def test_operator_can_edit_participant(admin_token):
    """
    Проверяет, что Оператор может редактировать участников.
    """
    with TestClient(app) as client:
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Админ создает Оператора и Участника
        op_data = {"username": "op_editor", "password": "password123", "role": "Operator"}
        client.post("/system-users/", json=op_data, headers=admin_headers)
        
        p_resp = client.post("/participants/", json={"full_name": "To Edit", "email": "edit@me.com"}, headers=admin_headers)
        p_id = p_resp.json()["id"]

        # 2. Логинимся как Оператор
        token = client.post("/token", data={"username": "op_editor", "password": "password123"}).json()["access_token"]
        op_headers = {"Authorization": f"Bearer {token}"}

        # 3. Оператор редактирует участника -> 200 OK
        upd_resp = client.put(f"/participants/{p_id}", json={"full_name": "Edited by Operator"}, headers=op_headers)
        assert upd_resp.status_code == 200
        assert upd_resp.json()["full_name"] == "Edited by Operator"

def test_registrar_restrictions(admin_token):
    """
    Проверяет, что Регистратор НЕ может создавать события, но может искать участников.
    """
    with TestClient(app) as client:
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Создаем Регистратора
        reg_data = {"username": "reg_user_test", "password": "password", "role": "Registrar"}
        # Если пользователь уже есть, игнорируем ошибку
        client.post("/system-users/", json=reg_data, headers=admin_headers)

        token = client.post("/token", data={"username": "reg_user_test", "password": "password"}).json()["access_token"]
        reg_headers = {"Authorization": f"Bearer {token}"}

        # 2. Попытка создать событие -> 403
        resp = client.post("/events/", json={"title": "Hack", "event_date": "2025-01-01T10:00:00"}, headers=reg_headers)
        assert resp.status_code == 403
        
        # 3. Попытка создать участника -> 403 (Регистратор не может создавать)
        resp_create = client.post("/participants/", json={"full_name": "Hack P"}, headers=reg_headers)
        assert resp_create.status_code == 403

        # 4. Попытка редактировать участника -> 403
        # Сначала создадим участника админом
        p_resp = client.post("/participants/", json={"full_name": "Reg Check", "email": "reg@check.com"}, headers=admin_headers)
        p_id = p_resp.json()["id"]
        
        resp_edit = client.put(f"/participants/{p_id}", json={"full_name": "Hacked Name"}, headers=reg_headers)
        assert resp_edit.status_code == 403

        # 5. Попытка найти участника -> 200
        search_resp = client.get("/participants/search/?query=Reg", headers=reg_headers)
        assert search_resp.status_code == 200
        assert len(search_resp.json()) > 0
