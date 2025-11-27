from fastapi import FastAPI, HTTPException, Depends, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from datetime import datetime

# Импортируем зависимости и модели из локальных файлов
# ИСПОЛЬЗУЕМ АБСОЛЮТНЫЕ ИМПОРТЫ ДЛЯ ИЗБЕЖАНИЯ ОШИБКИ "attempted relative import"
import models, schemas 
from database import get_db

# --- Константы (для имитации авторизации) ---
# В реальном приложении этот ID берется из токена авторизации
MOCK_SYSTEM_USER_ID = 1

# --- Приложение FastAPI ---

app = FastAPI(
    title="Event Registration API v3 (Roles, Registrars, Directories)",
    description="API для управления регистрацией с разделением ролей (Admin/Registrar) и справочниками.",
    version="3.0.0"
)

# ------------------------------------------------------
# --- МАРШРУТЫ СИСТЕМНЫХ ПОЛЬЗОВАТЕЛЕЙ (SystemUser) ---
# ------------------------------------------------------

@app.post("/system-users/", response_model=schemas.SystemUserRead)
async def create_system_user(
    user: schemas.SystemUserCreate, 
    db: AsyncSession = Depends(get_db)
):
    """Создает нового системного пользователя (Администратора или Регистратора)."""
    
    # 1. Проверка уникальности username 
    stmt = select(models.SystemUser).filter(
        models.SystemUser.username == user.username
    )
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(
            status_code=400, 
            detail=f"Системный пользователь с именем '{user.username}' уже существует."
        )

    db_user = models.SystemUser(**user.dict())
    
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    
    return db_user

@app.get("/system-users/", response_model=List[schemas.SystemUserRead])
async def list_system_users(db: AsyncSession = Depends(get_db)):
    """Получает список всех системных пользователей."""
    stmt = select(models.SystemUser)
    result = await db.execute(stmt)
    return result.scalars().all()

# ------------------------------------------------------
# --- МАРШРУТЫ МЕРОПРИЯТИЙ (Event) ---
# ------------------------------------------------------

@app.post("/events/", response_model=schemas.EventRead)
async def create_event(event: schemas.EventCreate, db: AsyncSession = Depends(get_db)):
    """Создает новое мероприятие."""
    
    # --- ИСПРАВЛЕНИЕ ОШИБКИ DATETIME ---
    # Преобразуем объект Pydantic в словарь
    event_data = event.dict()
    
    # Удаляем информацию о часовом поясе, чтобы соответствовать PostgreSQL TIMESTAMP WITHOUT TIME ZONE
    if event_data.get('event_date') and event_data['event_date'].tzinfo is not None:
        event_data['event_date'] = event_data['event_date'].replace(tzinfo=None)
    # -----------------------------------
    
    db_event = models.Event(**event_data)
    
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    
    return db_event

@app.get("/events/{event_id}", response_model=schemas.EventRead)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """Получает информацию о мероприятии по ID."""
    event = await db.get(models.Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")
    return event


# ------------------------------------------------------
# --- МАРШРУТЫ УЧАСТНИКОВ (Participant) ---
# ------------------------------------------------------

@app.post("/participants/", response_model=schemas.ParticipantRead)
async def create_participant(
    participant: schemas.ParticipantCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Создает нового участника (того, кто будет регистрироваться). 
    Проверяет уникальность по ФИО и Примечанию.
    """
    
    # 1. Проверка уникальности (ФИО + Примечание)
    stmt = select(models.Participant).filter(
        models.Participant.full_name == participant.full_name,
        models.Participant.note == participant.note
    )
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(
            status_code=400, 
            detail="Участник с таким ФИО и Примечанием уже существует."
        )

    db_participant = models.Participant(**participant.dict())
    
    db.add(db_participant)
    await db.commit()
    await db.refresh(db_participant)
    
    return db_participant

# --- МАРШРУТ ДЛЯ МАССОВОГО СОЗДАНИЯ УЧАСТНИКОВ ---
@app.post("/participants/bulk/", response_model=List[schemas.ParticipantRead])
async def bulk_create_participants(
    participants: List[schemas.ParticipantCreate], 
    db: AsyncSession = Depends(get_db)
):
    """
    Создает несколько участников за один запрос (массовое заполнение). 
    Пропускает участников, которые уже существуют (по ФИО + Примечанию).
    """
    new_participants = []
    
    for participant_data in participants:
        # 1. Проверка уникальности (ФИО + Примечание)
        stmt = select(models.Participant).filter(
            models.Participant.full_name == participant_data.full_name,
            models.Participant.note == participant_data.note
        )
        result = await db.execute(stmt)
        if result.scalars().first():
            print(f"Участник '{participant_data.full_name}' ({participant_data.note}) уже существует и был пропущен.")
            continue

        db_participant = models.Participant(**participant_data.dict())
        db.add(db_participant)
        new_participants.append(db_participant)

    await db.commit()
    
    # Обновляем созданные объекты для получения ID и других полей
    for p in new_participants:
        await db.refresh(p)
        
    return new_participants

# --- МАРШРУТ ДЛЯ СПИСКА УЧАСТНИКОВ С ПАГИНАЦИЕЙ ---
@app.get("/participants/", response_model=List[schemas.ParticipantRead])
async def list_participants(
    limit: int = Query(100, ge=1, le=500, description="Максимальное количество участников (до 500)"), 
    offset: int = Query(0, ge=0, description="Смещение для пагинации"), 
    db: AsyncSession = Depends(get_db)
):
    """Получает список всех участников с поддержкой пагинации (по 100 по умолчанию)."""
        
    stmt = select(models.Participant).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()

# --- МАРШРУТ ДЛЯ ПОИСКА УЧАСТНИКОВ В СИСТЕМЕ ---
@app.get("/participants/search/", response_model=List[schemas.ParticipantRead])
async def search_participants(
    query: str = Query(..., description="Строка поиска по ФИО, email или примечанию"), 
    limit: int = Query(100, ge=1, le=500), 
    db: AsyncSession = Depends(get_db)
):
    """Поиск участников по ФИО, email или примечанию."""
    search_pattern = f"%{query}%"
    
    stmt = select(models.Participant).filter(
        (models.Participant.full_name.ilike(search_pattern)) |
        (models.Participant.email.ilike(search_pattern)) |
        (models.Participant.note.ilike(search_pattern))
    ).limit(limit)
    
    result = await db.execute(stmt)
    return result.scalars().all()
# ------------------------------------------------------

# ------------------------------------------------------
# --- МАРШРУТЫ СПРАВОЧНИКОВ (Directory) ---
# ------------------------------------------------------

@app.post("/directories/", response_model=schemas.DirectoryRead)
async def create_directory(directory: schemas.DirectoryCreate, db: AsyncSession = Depends(get_db)):
    """Создает новый справочник/группу участников."""
    
    db_directory = models.Directory(**directory.dict())
    
    db.add(db_directory)
    await db.commit()
    await db.refresh(db_directory)
    
    return db_directory

@app.get("/directories/", response_model=List[schemas.DirectoryRead])
async def list_directories(db: AsyncSession = Depends(get_db)):
    """Получает список всех справочников."""
    stmt = select(models.Directory)
    result = await db.execute(stmt)
    return result.scalars().all()

@app.post("/directories/add-member/", response_model=schemas.DirectoryMembershipCreate)
async def add_member_to_directory(membership: schemas.DirectoryMembershipCreate, db: AsyncSession = Depends(get_db)):
    """Добавляет участника в справочник."""
    
    # Проверка, что Participant и Directory существуют
    if not await db.get(models.Participant, membership.participant_id):
        raise HTTPException(status_code=404, detail="Участник не найден.")
    if not await db.get(models.Directory, membership.directory_id):
        raise HTTPException(status_code=404, detail="Справочник не найден.")
        
    db_membership = models.DirectoryMembership(**membership.dict())
    
    try:
        db.add(db_membership)
        await db.commit()
    except Exception:
        # Это сработает, если UniqueConstraint сработает (участник уже в справочнике)
        raise HTTPException(status_code=400, detail="Участник уже состоит в этом справочнике.")
    
    return membership

# --- МАРШРУТ ДЛЯ СПИСКА УЧАСТНИКОВ СПРАВОЧНИКА С ПОИСКОМ ---
@app.get("/directories/{directory_id}/members/", response_model=List[schemas.ParticipantRead])
async def list_directory_members(
    directory_id: int, 
    query: Optional[str] = Query(None, description="Строка поиска по ФИО, email или примечанию"), 
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Получает список участников справочника с возможностью поиска по ФИО/email/note."""
    
    # 1. Проверка существования Directory
    if not await db.get(models.Directory, directory_id):
        raise HTTPException(status_code=404, detail="Справочник не найден.")
        
    # Базовый запрос: участники, которые являются членами этого справочника
    stmt = select(models.Participant).join(
        models.DirectoryMembership, models.Participant.id == models.DirectoryMembership.participant_id
    ).filter(
        models.DirectoryMembership.directory_id == directory_id
    )
    
    # 2. Добавление условия поиска, если указан query
    if query:
        search_pattern = f"%{query}%"
        stmt = stmt.filter(
            (models.Participant.full_name.ilike(search_pattern)) |
            (models.Participant.email.ilike(search_pattern)) |
            (models.Participant.note.ilike(search_pattern))
        )

    # 3. Применение лимита
    stmt = stmt.limit(limit)
    
    result = await db.execute(stmt)
    return result.scalars().all()
# ------------------------------------------------------


# ------------------------------------------------------
# --- МАРШРУТЫ РЕГИСТРАЦИИ (Registration) ---
# ------------------------------------------------------

@app.post("/events/{event_id}/register/", response_model=List[schemas.RegistrationRead])
async def register_users(
    event_id: int, 
    participant_ids: Optional[List[int]] = Body(None, description="Список ID участников для регистрации"),
    directory_id: Optional[int] = Body(None, description="ID справочника для регистрации"),
    db: AsyncSession = Depends(get_db)
):
    """
    Регистрирует одного или нескольких пользователей на мероприятие.
    Может принимать список ID участников или ID справочника, или оба.
    """
    
    registered_by_user_id = MOCK_SYSTEM_USER_ID 

    # 1. Проверка существования Event
    event = await db.get(models.Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Мероприятие с id {event_id} не найдено.")
    if not event.registration_active:
        raise HTTPException(status_code=403, detail=f"Регистрация на мероприятие {event_id} не активна.")
    
    # 2. Сбор списка participant_ids для регистрации
    target_participant_ids = set(participant_ids if participant_ids else [])

    if directory_id:
        directory = await db.get(models.Directory, directory_id)
        if not directory:
            raise HTTPException(status_code=404, detail=f"Справочник с id {directory_id} не найден.")
            
        # Получаем ID участников из справочника
        stmt_dir_members = select(models.DirectoryMembership.participant_id).filter(
            models.DirectoryMembership.directory_id == directory_id
        )
        result_members = await db.execute(stmt_dir_members)
        directory_members = result_members.scalars().all()
        
        target_participant_ids.update(directory_members)
        
    if not target_participant_ids:
        raise HTTPException(status_code=400, detail="Не указаны участники для регистрации.")
        
    # 3. Проведение регистрации для каждого участника
    successful_registrations = []
    
    # Получаем уже зарегистрированных участников, чтобы избежать ошибок UniqueConstraint
    stmt_existing = select(models.Registration.participant_id).filter(
        models.Registration.event_id == event_id,
        models.Registration.participant_id.in_(target_participant_ids)
    )
    result_existing = await db.execute(stmt_existing)
    existing_participant_ids = set(result_existing.scalars().all())

    participants_to_register = target_participant_ids - existing_participant_ids
    
    for p_id in participants_to_register:
        # Проверка, что Participant существует
        participant_check = await db.get(models.Participant, p_id)
        if not participant_check:
            print(f"Участник с ID {p_id} не существует и был пропущен.")
            continue

        db_registration = models.Registration(
            event_id=event_id, 
            participant_id=p_id,
            registered_by_user_id=registered_by_user_id
        )
        db.add(db_registration)
        successful_registrations.append(db_registration)

    await db.commit()

    # Обновляем все созданные регистрации для возврата данных
    for reg in successful_registrations:
        await db.refresh(reg)

    return successful_registrations

# ------------------------------------------------------
# --- МАРШРУТЫ СТАТУСА (Event Participants Status) ---
# ------------------------------------------------------

@app.get("/events/{event_id}/participants/", response_model=List[schemas.ParticipantStatus])
async def get_event_participants(
    event_id: int, 
    query: Optional[str] = Query(None, description="Строка поиска по ФИО, email или примечанию"), # Добавлен поиск
    limit: int = Query(100, ge=1, le=500), # Добавлено ограничение выборки
    db: AsyncSession = Depends(get_db)
):
    """
    Получает список всех участников мероприятия с их статусом явки и информацией о регистраторе,
    с возможностью поиска по ФИО/email/note.
    """
    
    # SQL-запрос с явными JOIN для получения данных из Participant, Registration и SystemUser
    stmt = select(
        models.Participant, 
        models.Registration.arrival_time, 
        models.SystemUser.full_name.label("registered_by_full_name"),
        models.SystemUser.role.label("registered_by_role")
    ).join(
        models.Registration, models.Participant.id == models.Registration.participant_id
    ).join(
        models.SystemUser, models.Registration.registered_by_user_id == models.SystemUser.id
    ).filter(
        models.Registration.event_id == event_id
    )

    # Добавление условия поиска, если указан query
    if query:
        search_pattern = f"%{query}%"
        stmt = stmt.filter(
            (models.Participant.full_name.ilike(search_pattern)) |
            (models.Participant.email.ilike(search_pattern)) |
            (models.Participant.note.ilike(search_pattern))
        )
    
    # Применение лимита
    stmt = stmt.limit(limit)
    
    result = await db.execute(stmt)
    
    participants_status = []
    
    # Итерируемся по результатам, преобразуя их в схему ParticipantStatus
    for participant_orm, arrival_time, reg_full_name, reg_role in result.all():
        # Преобразуем ORM-объект Participant в Pydantic-словарь
        participant_dict = schemas.ParticipantRead.from_orm(participant_orm).dict()
        
        # Создаем финальный объект ParticipantStatus, добавляя поля из JOIN
        participant_data = schemas.ParticipantStatus(
            **participant_dict,
            arrival_time=arrival_time,
            registered_by_full_name=reg_full_name,
            registered_by_role=reg_role
        )
        participants_status.append(participant_data)
            
    return participants_status