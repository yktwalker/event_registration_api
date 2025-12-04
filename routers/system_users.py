from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import models
import schemas
from database import get_db
from dependencies import get_current_admin, get_password_hash

router = APIRouter()

@router.post("/system-users/", response_model=schemas.SystemUserRead)
async def create_system_user(
    user: schemas.SystemUserCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
):
    stmt = select(models.SystemUser).filter(models.SystemUser.username == user.username)
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Пользователь с таким именем уже существует.")
    
    hashed_pwd = get_password_hash(user.password)
    db_user = models.SystemUser(
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        hashed_password=hashed_pwd,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.get("/system-users/", response_model=List[schemas.SystemUserRead])
async def list_system_users(
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
):
    stmt = select(models.SystemUser)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.put("/system-users/{user_id}", response_model=schemas.SystemUserRead)
async def update_system_user(
    user_id: int,
    user_update: schemas.SystemUserUpdate,
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
):
    user = await db.get(models.SystemUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    if user_update.role is not None:
        if user.id == admin_user.id and user_update.role != models.SystemUserRole.ADMIN:
             raise HTTPException(status_code=400, detail="Нельзя снять права администратора с самого себя.")
        user.role = user_update.role
    if user_update.password is not None:
        user.hashed_password = get_password_hash(user_update.password)
        
    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/system-users/{user_id}", status_code=204)
async def delete_system_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
):
    if user_id == admin_user.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя.")
        
    user = await db.get(models.SystemUser, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
        
    await db.delete(user)
    await db.commit()
    return None
