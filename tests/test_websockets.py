from fastapi.testclient import TestClient
from main import app

def test_websocket_connection():
    client = TestClient(app)
    with client.websocket_connect("/ws/events/1") as websocket:
        pass

def test_websocket_broadcast_scenario(admin_token):
    """
    Тест сценария WebSocket с использованием синхронного TestClient.
    """
    # Используем контекстный менеджер TestClient
    with TestClient(app) as client:
        auth_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Создаем Event
        event_data = {
            "title": "WS Test Event",
            "event_date": "2025-12-31T10:00:00",
            "registration_active": True
        }
        resp_event = client.post("/events/", json=event_data, headers=auth_headers)
        assert resp_event.status_code == 200
        event_id = resp_event.json()["id"]

        # 2. Создаем Participant
        p_data = {"full_name": "Socket User", "email": "socket@test.com"}
        p_resp = client.post("/participants/", json=p_data, headers=auth_headers)
        assert p_resp.status_code == 200
        participant_id = p_resp.json()["id"]

        # 3. WebSocket сценарий
        with client.websocket_connect(f"/ws/events/{event_id}") as websocket:
            
            # Регистрация (триггерит уведомление)
            # ИСПРАВЛЕНИЕ: Передаем словарь с ключом participant_ids
            reg_resp = client.post(
                f"/events/{event_id}/register/",
                json={"participant_ids": [participant_id]}, 
                headers=auth_headers
            )
            assert reg_resp.status_code == 200
            
            # Получаем уведомление
            data = websocket.receive_json()
            assert data["type"] == "new_registrations"
            assert participant_id in data["participant_ids"]
            
            # Удаление регистрации (триггерит уведомление)
            del_resp = client.delete(
                f"/events/{event_id}/participants/{participant_id}",
                headers=auth_headers
            )
            assert del_resp.status_code == 204
            
            # Получаем уведомление об удалении
            data_del = websocket.receive_json()
            assert data_del["type"] == "deleted_registration"
            assert data_del["participant_id"] == participant_id
