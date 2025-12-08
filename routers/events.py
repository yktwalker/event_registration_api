from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func  # Добавлен импорт func
import models
import schemas
from database import get_db
from dependencies import get_current_user, get_current_operator_or_admin, get_current_registrar_or_admin

router = APIRouter()

@router.get("/events/", response_model=List[schemas.EventRead])
async def list_events(
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_user),
):
    stmt = select(models.Event)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/events/active", response_model=Optional[schemas.EventRead])
async def get_active_event_for_registrar(
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_registrar_or_admin),
):
    stmt = select(models.Event).filter(models.Event.registration_active == True)
    result = await db.execute(stmt)
    return result.scalars().first()

@router.get("/events/active/stats", response_model=schemas.EventStats)
async def get_active_event_stats(
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_registrar_or_admin),
):
    """
    Возвращает статистику по текущему активному мероприятию:
    - Название
    - Общее количество регистраций
    - Количество пришедших (есть arrival_time)
    """
    stmt_active = select(models.Event).filter(models.Event.registration_active == True)
    result_active = await db.execute(stmt_active)
    active_event = result_active.scalars().first()

    if not active_event:
        raise HTTPException(status_code=404, detail="Нет активного мероприятия")

    # Считаем общее количество регистраций
    stmt_total = select(func.count()).select_from(models.Registration).filter(
        models.Registration.event_id == active_event.id
    )
    result_total = await db.execute(stmt_total)
    total = result_total.scalar() or 0

    # Считаем количество пришедших
    stmt_arrived = select(func.count()).select_from(models.Registration).filter(
        models.Registration.event_id == active_event.id,
        models.Registration.arrival_time.is_not(None)
    )
    result_arrived = await db.execute(stmt_arrived)
    arrived = result_arrived.scalar() or 0

    return schemas.EventStats(
        event_title=active_event.title,
        total_registrants=total,
        arrived_participants=arrived
    )

@router.post("/events/", response_model=schemas.EventRead)
async def create_event(
    event: schemas.EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_operator_or_admin),
):
    if event.registration_active:
        stmt_active = select(models.Event).filter(models.Event.registration_active == True)
        result_active = await db.execute(stmt_active)
        existing_active = result_active.scalars().first()
        if existing_active:
            raise HTTPException(
                status_code=400,
                detail=f"Уже существует активное мероприятие (id={existing_active.id}, title='{existing_active.title}'). "
                       f"Сначала деактивируйте его."
            )

    event_data = event.model_dump()
    if event_data.get("event_date") and event_data["event_date"].tzinfo is not None:
        event_data["event_date"] = event_data["event_date"].replace(tzinfo=None)

    db_event = models.Event(**event_data)
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event

@router.put("/events/{event_id}", response_model=schemas.EventRead)
async def update_event(
    event_id: int,
    event_update: schemas.EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_operator_or_admin),
):
    event = await db.get(models.Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")

    if event_update.registration_active is True:
        stmt_active = select(models.Event).filter(
            models.Event.registration_active == True,
            models.Event.id != event_id
        )
        result_active = await db.execute(stmt_active)
        existing_active = result_active.scalars().first()
        if existing_active:
            raise HTTPException(
                status_code=400,
                detail=f"Уже существует активное мероприятие (id={existing_active.id}). "
                       f"Сначала деактивируйте его."
            )

    update_data = event_update.model_dump(exclude_unset=True)
    
    if "event_date" in update_data and update_data["event_date"] and update_data["event_date"].tzinfo is not None:
        update_data["event_date"] = update_data["event_date"].replace(tzinfo=None)

    for key, value in update_data.items():
        setattr(event, key, value)

    await db.commit()
    await db.refresh(event)
    return event

@router.get("/events/{event_id}", response_model=schemas.EventRead)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)):
    event = await db.get(models.Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")
    return event

@router.delete("/events/{event_id}", status_code=204)
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_operator_or_admin),
):
    event = await db.get(models.Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")
    
    await db.delete(event)
    await db.commit()
    return None
