import pytest
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient

from models import Participant, Event, Registration, Directory, DirectoryMembership, SystemUser

@pytest.mark.asyncio
async def test_participant_cascade_deletion(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str
):
    """
    Проверяет, что при удалении участника удаляются:
    1. Его регистрации на мероприятия (Registration)
    2. Его членство в справочниках (DirectoryMembership)
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Подготовка данных: создаем Event, Directory и Participant
    # event_date передаем как объект datetime
    event = Event(title="Cascade Test Event", event_date=datetime(2025, 12, 31, 12, 0, 0))
    directory = Directory(name="Cascade Test Directory")
    participant = Participant(full_name="To Be Deleted", email="delete@me.com")
    
    # Получаем админа для поля registered_by
    stmt_admin = select(SystemUser).filter_by(username="admin")
    admin = (await db_session.execute(stmt_admin)).scalars().first()

    db_session.add_all([event, directory, participant])
    await db_session.commit()
    
    # Обновляем объекты, чтобы получить их ID
    await db_session.refresh(participant)
    await db_session.refresh(event)
    await db_session.refresh(directory)

    # 2. Создаем связи: Регистрацию и Членство в справочнике
    registration = Registration(
        event_id=event.id,
        participant_id=participant.id,
        registered_by_user_id=admin.id
    )
    membership = DirectoryMembership(
        directory_id=directory.id,
        participant_id=participant.id
    )
    
    db_session.add_all([registration, membership])
    await db_session.commit()
    
    # Запоминаем ID для проверки после удаления
    p_id = participant.id
    reg_id = registration.id
    mem_id = membership.id

    # Убеждаемся, что связи созданы перед тестом
    assert (await db_session.get(Registration, reg_id)) is not None
    assert (await db_session.get(DirectoryMembership, mem_id)) is not None

    # 3. УДАЛЕНИЕ УЧАСТНИКА через API
    response = await client.delete(f"/participants/{p_id}", headers=headers)
    assert response.status_code == 204

    # 4. ПРОВЕРКИ: Все должно исчезнуть
    
    # ВАЖНО: Синхронный вызов expire_all() (без await), 
    # чтобы сбросить кеш сессии и заставить SQLAlchemy сделать новый SELECT
    db_session.expire_all()
    
    # Участник удален?
    deleted_participant = await db_session.get(Participant, p_id)
    assert deleted_participant is None

    # Регистрация удалена? (Проверка каскада)
    deleted_registration = await db_session.get(Registration, reg_id)
    assert deleted_registration is None

    # Членство в справочнике удалено? (Проверка каскада)
    deleted_membership = await db_session.get(DirectoryMembership, mem_id)
    assert deleted_membership is None
