import pytest
from main import app
from fastapi.testclient import TestClient

def test_operator_can_create_event_but_not_user(admin_token):
    """
    Проверяет, что Оператор может создавать события, но не пользователей.
    """
    with TestClient(app) as client:
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Админ создает Оператора
        op_data = {
            "username": "op_user",
            "password": "password123",
            "role": "Operator"
        }
        # Удаляем старого если есть (для идемпотентности) или просто создаем
        # В рамках одного теста БД чистая (обычно), если фикстуры настроены верно.
        # Если нет - можно проверить статус.
        
        resp = client.post("/system-users/", json=op_data, headers=admin_headers)
        # Если уже есть, ок, идем дальше (значит остался с прошлого запуска если БД не сбрасывалась)
        if resp.status_code != 200 and resp.status_code != 400:
             assert resp.status_code == 200

        # 2. Логинимся как Оператор
        login_resp = client.post("/token", data={"username": "op_user", "password": "password123"})
        assert login_resp.status_code == 200
        op_token = login_resp.json()["access_token"]
        op_headers = {"Authorization": f"Bearer {op_token}"}

        # 3. Оператор создает событие -> ДОЛЖНО БЫТЬ 200 OK
        event_data = {
            "title": "Operator Event",
            "event_date": "2025-06-01T10:00:00"
        }
        e_resp = client.post("/events/", json=event_data, headers=op_headers)
        assert e_resp.status_code == 200

        # 4. Оператор пытается создать системного пользователя -> ДОЛЖНО БЫТЬ 403 FORBIDDEN
        new_user_data = {
            "username": "hacker",
            "password": "123",
            "role": "Admin"
        }
        u_resp = client.post("/system-users/", json=new_user_data, headers=op_headers)
        assert u_resp.status_code == 403

def test_registrar_restrictions(admin_token):
    """
    Проверяет, что Регистратор НЕ может создавать события, но может искать участников.
    """
    with TestClient(app) as client:
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Создаем Регистратора
        reg_data = {"username": "reg_user_test", "password": "password", "role": "Registrar"}
        # Если пользователь уже есть, игнорируем ошибку (для упрощения)
        client.post("/system-users/", json=reg_data, headers=admin_headers)
        
        token = client.post("/token", data={"username": "reg_user_test", "password": "password"}).json()["access_token"]
        reg_headers = {"Authorization": f"Bearer {token}"}

        # 2. Попытка создать событие -> 403
        resp = client.post("/events/", json={"title": "Hack", "event_date": "2025-01-01T10:00:00"}, headers=reg_headers)
        assert resp.status_code == 403

        # 3. Попытка найти участника -> 200 (Мы это исправили в main.py)
        # Сначала админ создаст участника, чтобы было кого искать
        # <--- ИСПРАВЛЕНИЕ ЗДЕСЬ: Добавлен email
        client.post("/participants/", json={"full_name": "Find Me", "email": "findme@example.com"}, headers=admin_headers)
        
        search_resp = client.get("/participants/search/?query=Find", headers=reg_headers)
        assert search_resp.status_code == 200
        assert len(search_resp.json()) > 0
