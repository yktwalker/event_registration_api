import json
from typing import List, Optional
from datetime import datetime, timezone, UTC
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import and_, or_, desc, asc, nulls_last

import models
import schemas
from database import get_db
from dependencies import get_current_registrar_or_admin, get_current_operator_or_admin
from manager import manager

router = APIRouter()

@router.post("/events/{event_id}/sync/", response_model=schemas.SyncResponse)
async def sync_registrations(
    event_id: int,
    sync_req: schemas.SyncRequest,
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_registrar_or_admin),
):
    server_time = datetime.now(UTC)
    stmt = (
        select(models.Registration)
        .options(joinedload(models.Registration.registered_by))
        .filter(models.Registration.event_id == event_id)
    )

    conditions = []
    if sync_req.last_sync_time:
        last_sync = sync_req.last_sync_time
        if last_sync.tzinfo:
            last_sync = last_sync.astimezone(timezone.utc).replace(tzinfo=None)
        conditions.append(models.Registration.registration_time > last_sync)
    
    if sync_req.known_registration_ids:
        conditions.append(models.Registration.id.not_in(sync_req.known_registration_ids))

    if conditions:
        stmt = stmt.filter(and_(*conditions))

    result = await db.execute(stmt)
    registrations_orm = result.scalars().all()

    registrations_pydantic = [
        schemas.RegistrationRead.model_validate(reg) for reg in registrations_orm
    ]

    current_user.last_sync_time = server_time
    await db.commit()

    return schemas.SyncResponse(
        new_registrations=registrations_pydantic,
        server_time=server_time,
    )

@router.post("/events/{event_id}/register/", response_model=List[schemas.RegistrationRead])
async def register_users(
    event_id: int,
    participant_ids: Optional[List[int]] = Body(None),
    directory_id: Optional[int] = Body(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_operator_or_admin),
):
    reg_user_id = current_user.id
    reg_username = current_user.username
    reg_role = current_user.role
    reg_fullname = current_user.full_name

    event = await db.get(models.Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Мероприятие {event_id} не найдено.")
    
    if not event.registration_active:
        raise HTTPException(status_code=403, detail="Регистрация закрыта.")

    target_participant_ids = set(participant_ids or [])

    if directory_id:
        directory = await db.get(models.Directory, directory_id)
        if not directory:
            raise HTTPException(status_code=404, detail=f"Справочник {directory_id} не найден.")
        
        stmt_dir_members = select(models.DirectoryMembership.participant_id).filter(
            models.DirectoryMembership.directory_id == directory_id
        )
        result_members = await db.execute(stmt_dir_members)
        target_participant_ids.update(result_members.scalars().all())

    if not target_participant_ids:
        raise HTTPException(status_code=400, detail="Не указаны участники.")

    stmt_existing = select(models.Registration.participant_id).filter(
        models.Registration.event_id == event_id,
        models.Registration.participant_id.in_(target_participant_ids)
    )
    result_existing = await db.execute(stmt_existing)
    existing_ids = set(result_existing.scalars().all())

    participants_to_register = target_participant_ids - existing_ids
    
    successful_registrations: list[models.Registration] = []

    for p_id in participants_to_register:
        if not await db.get(models.Participant, p_id):
            continue
        
        db_registration = models.Registration(
            event_id=event_id,
            participant_id=p_id,
            registered_by_user_id=reg_user_id,
        )
        db.add(db_registration)
        successful_registrations.append(db_registration)

    await db.commit()

    response_data: list[dict] = []
    for reg in successful_registrations:
        await db.refresh(reg)
        response_data.append(
            {
                "id": reg.id,
                "event_id": reg.event_id,
                "participant_id": reg.participant_id,
                "registered_by_user_id": reg.registered_by_user_id,
                "registration_time": reg.registration_time,
                "arrival_time": reg.arrival_time,
                "registered_by": {
                    "id": reg_user_id,
                    "username": reg_username,
                    "full_name": reg_fullname,
                    "role": reg_role,
                },
            }
        )

    if successful_registrations:
        notify_data = {
            "type": "new_registrations",
            "registrar_id": reg_user_id,
            "registrar_name": reg_username,
            "ids": [r.id for r in successful_registrations],
            "participant_ids": [r.participant_id for r in successful_registrations],
        }
        await manager.broadcast(json.dumps(notify_data), event_id)

    return response_data

@router.put("/events/{event_id}/participants/{participant_id}/arrival", response_model=schemas.RegistrationRead)
async def set_participant_arrival(
    event_id: int,
    participant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_registrar_or_admin),
):
    stmt = (
        select(models.Registration)
        .filter(
            models.Registration.event_id == event_id,
            models.Registration.participant_id == participant_id,
        )
        .options(joinedload(models.Registration.registered_by))
    )
    result = await db.execute(stmt)
    registration = result.scalars().first()
    if not registration:
        raise HTTPException(
            status_code=404, 
            detail="Участник не зарегистрирован на это мероприятие",
            )

    # ключевая правка: сохраняем наивное UTC-время
    now_utc_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    registration.arrival_time = now_utc_naive

    await db.commit()
    await db.refresh(registration)

    notify_data = {
        "type": "arrival_update",
        "registration_id": registration.id,
        "participant_id": participant_id,
        "arrival_time": registration.arrival_time.isoformat(),
        "action": "set",
    }
    await manager.broadcast(json.dumps(notify_data), event_id)

    return registration

@router.delete("/events/{event_id}/participants/{participant_id}/arrival", status_code=204)
async def unset_participant_arrival(
    event_id: int,
    participant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_registrar_or_admin),
):
    stmt = select(models.Registration).filter(
        models.Registration.event_id == event_id,
        models.Registration.participant_id == participant_id
    )
    
    result = await db.execute(stmt)
    registration = result.scalars().first()

    if not registration:
        raise HTTPException(status_code=404, detail="Регистрация не найдена.")

    # !!! ВАЖНО: Сохраняем ID до коммита, чтобы избежать ошибки MissingGreenlet
    # при обращении к expired объекту
    reg_id = registration.id

    # Очищаем поле
    registration.arrival_time = None
    
    await db.commit()

    # Оповещаем об отмене прибытия
    notify_data = {
        "type": "arrival_update",
        "registration_id": reg_id, # Используем сохраненную переменную
        "participant_id": participant_id,
        "arrival_time": None,
        "action": "unset"
    }
    await manager.broadcast(json.dumps(notify_data), event_id)
    
    return None

@router.delete("/events/{event_id}/participants/{participant_id}", status_code=204)
async def unregister_participant(
    event_id: int,
    participant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_operator_or_admin),
):
    stmt = select(models.Registration).filter(
        models.Registration.event_id == event_id,
        models.Registration.participant_id == participant_id
    )
    result = await db.execute(stmt)
    registration = result.scalars().first()

    if not registration:
        raise HTTPException(status_code=404, detail="Регистрация не найдена.")

    reg_id = registration.id
    await db.delete(registration)
    await db.commit()

    notify_data = {
        "type": "deleted_registration",
        "registration_id": reg_id,
        "participant_id": participant_id,
    }
    await manager.broadcast(json.dumps(notify_data), event_id)

    return None

@router.get("/events/{event_id}/participants/", response_model=List[schemas.ParticipantStatus])
async def get_event_participants(
    event_id: int,
    query: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_registrar_or_admin),
):
    stmt = select(
        models.Participant.id,
        models.Participant.full_name,
        models.Participant.email,
        models.Participant.phone,
        models.Participant.note,
        models.Registration.arrival_time,
        models.SystemUser.username.label("registered_by_full_name"),
        models.SystemUser.role.label("registered_by_role"),
    ).join(
        models.Registration,
        models.Participant.id == models.Registration.participant_id,
    ).join(
        models.SystemUser,
        models.Registration.registered_by_user_id == models.SystemUser.id,
    ).filter(models.Registration.event_id == event_id)

    if query:
        search_pattern = f"%{query}%"
        stmt = stmt.filter(
            or_(
                models.Participant.full_name.ilike(search_pattern),
                models.Participant.email.ilike(search_pattern),
                models.Participant.note.ilike(search_pattern),
            )
        )

    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    rows = result.all()

    participants_status = []
    if rows:
        participant_ids = [row.id for row in rows]
        stmt_dirs = select(
            models.DirectoryMembership.participant_id,
            models.Directory.id.label("dir_id"),
            models.Directory.name.label("dir_name"),
        ).join(
            models.Directory,
            models.DirectoryMembership.directory_id == models.Directory.id,
        ).filter(models.DirectoryMembership.participant_id.in_(participant_ids))

        dirs_result = await db.execute(stmt_dirs)
        dirs_map = {}
        for p_id, d_id, d_name in dirs_result.all():
            if p_id not in dirs_map:
                dirs_map[p_id] = []
            dirs_map[p_id].append({"id": d_id, "name": d_name})

        for row in rows:
            p_dirs = dirs_map.get(row.id, [])
            status_obj = schemas.ParticipantStatus(
                id=row.id,
                full_name=row.full_name,
                email=row.email,
                phone=row.phone,
                note=row.note,
                directories=p_dirs,
                arrival_time=row.arrival_time,
                registered_by_full_name=row.registered_by_full_name,
                registered_by_role=row.registered_by_role,
            )
            participants_status.append(status_obj)

    return participants_status

@router.get(
    "/events/{event_id}/registrations/search",
    response_model=List[schemas.ParticipantStatus],
)
async def search_event_registrations(
    event_id: int,
    query: Optional[str] = Query(None, description="Поиск по имени, email или примечанию"),
    sort_by: str = Query(
        "alphabet",
        description="Сортировка: alphabet, arrival_time_desc, arrival_time_asc",
    ),
    filter_arrived: bool = Query(
        False, description="Если True, вернет только тех, у кого есть дата прибытия"
    ),
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(50, ge=1, le=500, description="Количество записей на странице"),
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_registrar_or_admin),
):
    stmt = select(
        models.Participant.id,
        models.Participant.full_name,
        models.Participant.email,
        models.Participant.phone,
        models.Participant.note,
        models.Registration.arrival_time,
        models.SystemUser.username.label("registered_by_full_name"),
        models.SystemUser.role.label("registered_by_role"),
    ).join(
        models.Registration,
        models.Participant.id == models.Registration.participant_id,
    ).join(
        models.SystemUser,
        models.Registration.registered_by_user_id == models.SystemUser.id,
    ).filter(models.Registration.event_id == event_id)

    # Поиск
    if query:
        search_pattern = f"%{query}%"
        stmt = stmt.filter(
            or_(
                models.Participant.full_name.ilike(search_pattern),
                models.Participant.email.ilike(search_pattern),
                models.Participant.note.ilike(search_pattern),
            )
        )

    # Фильтр только прибывших
    if filter_arrived:
        stmt = stmt.filter(models.Registration.arrival_time.isnot(None))

    # Сортировка
    if sort_by == "arrival_time_desc":
        stmt = stmt.order_by(nulls_last(desc(models.Registration.arrival_time)))
    elif sort_by == "arrival_time_asc":
        stmt = stmt.order_by(nulls_last(asc(models.Registration.arrival_time)))
    else:
        # По умолчанию по алфавиту
        stmt = stmt.order_by(models.Participant.full_name.asc())

    # Пагинация
    offset = (page - 1) * limit
    stmt = stmt.offset(offset).limit(limit)

    result = await db.execute(stmt)
    rows = result.all()

    participants_status = []
    if rows:
        participant_ids = [row.id for row in rows]
        
        stmt_dirs = select(
            models.DirectoryMembership.participant_id,
            models.Directory.id.label("dir_id"),
            models.Directory.name.label("dir_name"),
        ).join(
            models.Directory,
            models.DirectoryMembership.directory_id == models.Directory.id,
        ).filter(models.DirectoryMembership.participant_id.in_(participant_ids))

        dirs_result = await db.execute(stmt_dirs)
        
        dirs_map = {}
        for p_id, d_id, d_name in dirs_result.all():
            if p_id not in dirs_map:
                dirs_map[p_id] = []
            dirs_map[p_id].append({"id": d_id, "name": d_name})

        for row in rows:
            p_dirs = dirs_map.get(row.id, [])
            status_obj = schemas.ParticipantStatus(
                id=row.id,
                full_name=row.full_name,
                email=row.email,
                phone=row.phone,
                note=row.note,
                directories=p_dirs,
                arrival_time=row.arrival_time,
                registered_by_full_name=row.registered_by_full_name,
                registered_by_role=row.registered_by_role,
            )
            participants_status.append(status_obj)

    return participants_status
