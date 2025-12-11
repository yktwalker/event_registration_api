from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import models
import schemas
from database import get_db
from dependencies import get_current_operator_or_admin, get_current_registrar_or_admin

router = APIRouter()

@router.post("/directories/", response_model=schemas.DirectoryRead)
async def create_directory(
    directory: schemas.DirectoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_operator_or_admin),
):
    db_directory = models.Directory(**directory.model_dump())
    db.add(db_directory)
    await db.commit()
    await db.refresh(db_directory)
    return db_directory

@router.get("/directories/", response_model=List[schemas.DirectoryRead])
async def list_directories(
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_registrar_or_admin),
):
    stmt = select(models.Directory)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.put("/directories/{directory_id}", response_model=schemas.DirectoryRead)
async def update_directory(
    directory_id: int,
    directory_update: schemas.DirectoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_operator_or_admin),
):
    directory = await db.get(models.Directory, directory_id)
    if not directory:
        raise HTTPException(status_code=404, detail="Справочник не найден")

    update_data = directory_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(directory, key, value)

    await db.commit()
    await db.refresh(directory)
    return directory

@router.delete("/directories/{directory_id}", status_code=204)
async def delete_directory(
    directory_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_operator_or_admin),
):
    directory = await db.get(models.Directory, directory_id)
    if not directory:
        raise HTTPException(status_code=404, detail="Справочник не найден")

    await db.delete(directory)
    await db.commit()
    return None

@router.post("/directories/add-member/", response_model=schemas.DirectoryMembershipCreate)
async def add_member_to_directory(
    membership: schemas.DirectoryMembershipCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_operator_or_admin),
):
    if not await db.get(models.Participant, membership.participant_id):
        raise HTTPException(status_code=404, detail="Участник не найден.")
    
    if not await db.get(models.Directory, membership.directory_id):
        raise HTTPException(status_code=404, detail="Справочник не найден.")

    db_membership = models.DirectoryMembership(**membership.model_dump())
    try:
        db.add(db_membership)
        await db.commit()
    except Exception:
        raise HTTPException(status_code=400, detail="Участник уже состоит в этом справочнике.")
    
    return membership

@router.delete("/directories/{directory_id}/members/{participant_id}", status_code=204)
async def remove_member_from_directory(
    directory_id: int,
    participant_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_operator_or_admin),
):
    stmt = select(models.DirectoryMembership).filter(
        models.DirectoryMembership.directory_id == directory_id,
        models.DirectoryMembership.participant_id == participant_id
    )
    result = await db.execute(stmt)
    membership = result.scalars().first()

    if not membership:
        raise HTTPException(status_code=404, detail="Участник не найден в этом справочнике")

    await db.delete(membership)
    await db.commit()
    return None

@router.get("/directories/{directory_id}/members/", response_model=List[schemas.ParticipantRead])
async def list_directory_members(
    directory_id: int,
    query: Optional[str] = Query(None),
    limit: int = Query(100, ge=1),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_registrar_or_admin),
):
    if not await db.get(models.Directory, directory_id):
        raise HTTPException(status_code=404, detail="Справочник не найден.")

    stmt = (
        select(models.Participant)
        .join(
            models.DirectoryMembership,
            models.Participant.id == models.DirectoryMembership.participant_id,
        )
        .filter(models.DirectoryMembership.directory_id == directory_id)
    )

    if query:
        search_pattern = f"%{query}%"
        stmt = stmt.filter(
            (models.Participant.full_name.ilike(search_pattern)) |
            (models.Participant.email.ilike(search_pattern)) |
            (models.Participant.note.ilike(search_pattern))
        )

    stmt = stmt.limit(limit).offset(offset)

    result = await db.execute(stmt)
    return result.scalars().all()
