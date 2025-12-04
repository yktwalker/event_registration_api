from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

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
    if not hasattr(models.Event, "description") and "description" in event_data:
        del event_data["description"]
        
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
