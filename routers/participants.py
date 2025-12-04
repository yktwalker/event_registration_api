from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload, joinedload

import models
import schemas
from database import get_db
from dependencies import get_current_operator_or_admin, get_current_registrar_or_admin, participant_to_schema

router = APIRouter()

@router.post("/participants/", response_model=schemas.ParticipantRead)
async def create_participant(
    participant: schemas.ParticipantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_operator_or_admin),
):
    stmt = select(models.Participant).filter(
        models.Participant.full_name == participant.full_name,
        models.Participant.note == participant.note,
    )
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Участник уже существует.")
        
    db_participant = models.Participant(**participant.model_dump())
    db.add(db_participant)
    await db.commit()
    
    # Просто refresh, directories будут пустыми (это безопасно)
    await db.refresh(db_participant)
    return db_participant

@router.post("/participants/bulk/", response_model=List[schemas.ParticipantRead])
async def bulk_create_participants(
    participants: List[schemas.ParticipantCreate],
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_operator_or_admin),
):
    new_participants: list[models.Participant] = []
    for participant_data in participants:
        stmt = select(models.Participant).filter(
            models.Participant.full_name == participant_data.full_name,
            models.Participant.note == participant_data.note,
        )
        result = await db.execute(stmt)
        if result.scalars().first():
            continue
            
        db_participant = models.Participant(**participant_data.model_dump())
        db.add(db_participant)
        new_participants.append(db_participant)
    
    await db.commit()
    for p in new_participants:
        await db.refresh(p)
    return new_participants

@router.get("/participants/{participant_id}", response_model=schemas.ParticipantRead)
async def get_participant(
    participant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_registrar_or_admin),
):
    stmt = (
        select(models.Participant)
        .options(
            selectinload(models.Participant.directory_memberships).joinedload(models.DirectoryMembership.directory)
        )
        .filter(models.Participant.id == participant_id)
    )
    result = await db.execute(stmt)
    participant = result.scalars().first()
    
    if not participant:
        raise HTTPException(status_code=404, detail="Участник не найден")
    
    return participant_to_schema(participant)

@router.get("/participants/", response_model=List[schemas.ParticipantRead])
async def list_participants(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_registrar_or_admin),
):
    stmt = (
        select(models.Participant)
        .options(
           selectinload(models.Participant.directory_memberships).joinedload(models.DirectoryMembership.directory)
        )
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    
    return [participant_to_schema(p) for p in result.scalars().all()]

@router.get("/participants/search/", response_model=List[schemas.ParticipantRead])
async def search_participants(
    query: str = Query(...),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_registrar_or_admin),
):
    search_pattern = f"%{query}%"
    stmt = (
        select(models.Participant)
        .options(
            selectinload(models.Participant.directory_memberships).joinedload(models.DirectoryMembership.directory)
        )
        .filter(
            (models.Participant.full_name.ilike(search_pattern)) |
            (models.Participant.email.ilike(search_pattern)) |
            (models.Participant.note.ilike(search_pattern))
        )
        .limit(limit)
    )
    result = await db.execute(stmt)
    
    return [participant_to_schema(p) for p in result.scalars().all()]

@router.put("/participants/{participant_id}", response_model=schemas.ParticipantRead)
async def update_participant(
    participant_id: int,
    participant_update: schemas.ParticipantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_operator_or_admin),
):
    participant = await db.get(models.Participant, participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Участник не найден")

    update_data = participant_update.model_dump(exclude_unset=True)

    if "full_name" in update_data or "note" in update_data:
        new_name = update_data.get("full_name", participant.full_name)
        new_note = update_data.get("note", participant.note)
        
        stmt_dup = select(models.Participant).filter(
            models.Participant.full_name == new_name,
            models.Participant.note == new_note,
            models.Participant.id != participant_id
        )
        result_dup = await db.execute(stmt_dup)
        if result_dup.scalars().first():
             raise HTTPException(status_code=400, detail="Участник с таким именем и примечанием уже существует.")

    for key, value in update_data.items():
        setattr(participant, key, value)

    await db.commit()
    await db.refresh(participant)
    
    return participant

@router.delete("/participants/{participant_id}", status_code=204)
async def delete_participant(
    participant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_operator_or_admin),
):
    participant = await db.get(models.Participant, participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Участник не найден")
        
    await db.delete(participant)
    await db.commit()
    return None
