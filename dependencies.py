import os
from datetime import datetime, timedelta, UTC
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import models
import schemas
from database import get_db

# --- Конфигурация ---
SECRET_KEY = os.getenv("SECRET_KEY", "MY_SUPER_SECRET_DEV_KEY_CHANGE_ME")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Auth Helpers ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- Dependencies ---
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> models.SystemUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception

    stmt = select(models.SystemUser).filter(models.SystemUser.username == token_data.username)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_admin(
    current_user: models.SystemUser = Depends(get_current_user),
) -> models.SystemUser:
    if current_user.role != models.SystemUserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Недостаточно прав. Требуется роль Администратора.")
    return current_user

async def get_current_operator_or_admin(
    current_user: models.SystemUser = Depends(get_current_user),
) -> models.SystemUser:
    if current_user.role not in (models.SystemUserRole.ADMIN, models.SystemUserRole.OPERATOR):
        raise HTTPException(
            status_code=403,
            detail="Недостаточно прав. Требуется роль Администратора или Оператора."
        )
    return current_user

async def get_current_registrar_or_admin(
    current_user: models.SystemUser = Depends(get_current_user),
) -> models.SystemUser:
    allowed = (models.SystemUserRole.ADMIN, models.SystemUserRole.REGISTRAR, models.SystemUserRole.OPERATOR)
    if current_user.role not in allowed:
        raise HTTPException(status_code=403, detail="Недостаточно прав.")
    return current_user

# --- Helpers ---
def participant_to_schema(participant: models.Participant) -> schemas.ParticipantRead:
    """Helper для ручного маппинга участников с директориями."""
    p_dto = schemas.ParticipantRead.model_validate(participant)
    if participant.directory_memberships:
         p_dto.directories = [
            schemas.DirectoryLink.model_validate(m.directory) 
            for m in participant.directory_memberships
            if m.directory
        ]
    return p_dto
