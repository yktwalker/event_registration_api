from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Body, Query, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import models, schemas
from database import get_db, init_db, AsyncSessionLocal, get_password_hash

SECRET_KEY = "MY_SUPER_SECRET_DEV_KEY_CHANGE_ME"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(
    title="Event Registration API (JWT)",
    description="API с JWT авторизацией и RBAC (Admin/Registrar), только одно активное мероприятие.",
    version="6.0.0",
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


@app.on_event("startup")
async def startup_event() -> None:
    async with AsyncSessionLocal() as session:
        await init_db(session)


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
        username = payload.get("sub")
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
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав. Требуется роль Администратора.")
    return current_user


async def get_current_registrar_or_admin(
    current_user: models.SystemUser = Depends(get_current_user),
) -> models.SystemUser:
    if current_user.role not in ("Admin", "Registrar"):
        raise HTTPException(status_code=403, detail="Недостаточно прав.")
    return current_user


@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(models.SystemUser).filter(models.SystemUser.username == form_data.username)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/system-users/", response_model=schemas.SystemUserRead)
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


@app.get("/system-users/", response_model=List[schemas.SystemUserRead])
async def list_system_users(
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
):
    stmt = select(models.SystemUser)
    result = await db.execute(stmt)
    return result.scalars().all()


@app.get("/events/", response_model=List[schemas.EventRead])
async def list_events(
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_user),
):
    stmt = select(models.Event)
    result = await db.execute(stmt)
    return result.scalars().all()


@app.get("/events/active", response_model=Optional[schemas.EventRead])
async def get_active_event_for_registrar(
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_registrar_or_admin),
):
    stmt = select(models.Event).filter(models.Event.registration_active == True)
    result = await db.execute(stmt)
    return result.scalars().first()


@app.post("/events/", response_model=schemas.EventRead)
async def create_event(
    event: schemas.EventCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
):
    stmt_active = select(models.Event).filter(models.Event.registration_active == True)
    result_active = await db.execute(stmt_active)
    existing_active = result_active.scalars().first()
    if existing_active:
        raise HTTPException(
            status_code=400,
            detail=f"Уже существует активное мероприятие (id={existing_active.id}, title='{existing_active.title}'). "
                   f"Сначала деактивируйте его.",
        )

    event_data = event.dict()
    if event_data.get("event_date") and event_data["event_date"].tzinfo is not None:
        event_data["event_date"] = event_data["event_date"].replace(tzinfo=None)

    db_event = models.Event(**event_data)
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event


@app.get("/events/{event_id}", response_model=schemas.EventRead)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)):
    event = await db.get(models.Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")
    return event


@app.delete("/events/{event_id}", status_code=204)
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
):
    event = await db.get(models.Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Мероприятие не найдено")
    await db.delete(event)
    await db.commit()
    return None


@app.post("/participants/", response_model=schemas.ParticipantRead)
async def create_participant(
    participant: schemas.ParticipantCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
):
    stmt = select(models.Participant).filter(
        models.Participant.full_name == participant.full_name,
        models.Participant.note == participant.note,
    )
    result = await db.execute(stmt)
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Участник уже существует.")

    db_participant = models.Participant(**participant.dict())
    db.add(db_participant)
    await db.commit()
    await db.refresh(db_participant)
    return db_participant


@app.post("/participants/bulk/", response_model=List[schemas.ParticipantRead])
async def bulk_create_participants(
    participants: List[schemas.ParticipantCreate],
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
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

        db_participant = models.Participant(**participant_data.dict())
        db.add(db_participant)
        new_participants.append(db_participant)

    await db.commit()
    for p in new_participants:
        await db.refresh(p)
    return new_participants


@app.get("/participants/", response_model=List[schemas.ParticipantRead])
async def list_participants(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
):
    stmt = select(models.Participant).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return result.scalars().all()


@app.get("/participants/search/", response_model=List[schemas.ParticipantRead])
async def search_participants(
    query: str = Query(...),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
):
    search_pattern = f"%{query}%"
    stmt = select(models.Participant).filter(
        (models.Participant.full_name.ilike(search_pattern))
        | (models.Participant.email.ilike(search_pattern))
        | (models.Participant.note.ilike(search_pattern))
    ).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@app.delete("/participants/{participant_id}", status_code=204)
async def delete_participant(
    participant_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
):
    participant = await db.get(models.Participant, participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Участник не найден")
    await db.delete(participant)
    await db.commit()
    return None


@app.post("/directories/", response_model=schemas.DirectoryRead)
async def create_directory(
    directory: schemas.DirectoryCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
):
    db_directory = models.Directory(**directory.dict())
    db.add(db_directory)
    await db.commit()
    await db.refresh(db_directory)
    return db_directory


@app.get("/directories/", response_model=List[schemas.DirectoryRead])
async def list_directories(
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
):
    stmt = select(models.Directory)
    result = await db.execute(stmt)
    return result.scalars().all()


@app.delete("/directories/{directory_id}", status_code=204)
async def delete_directory(
    directory_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
):
    directory = await db.get(models.Directory, directory_id)
    if not directory:
        raise HTTPException(status_code=404, detail="Справочник не найден")
    await db.delete(directory)
    await db.commit()
    return None


@app.post("/directories/add-member/", response_model=schemas.DirectoryMembershipCreate)
async def add_member_to_directory(
    membership: schemas.DirectoryMembershipCreate,
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
):
    if not await db.get(models.Participant, membership.participant_id):
        raise HTTPException(status_code=404, detail="Участник не найден.")
    if not await db.get(models.Directory, membership.directory_id):
        raise HTTPException(status_code=404, detail="Справочник не найден.")

    db_membership = models.DirectoryMembership(**membership.dict())
    try:
        db.add(db_membership)
        await db.commit()
    except Exception:
        raise HTTPException(status_code=400, detail="Участник уже состоит в этом справочнике.")
    return membership


@app.delete("/directories/{directory_id}/members/{participant_id}", status_code=204)
async def remove_member_from_directory(
    directory_id: int,
    participant_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
):
    stmt = select(models.DirectoryMembership).filter(
        models.DirectoryMembership.directory_id == directory_id,
        models.DirectoryMembership.participant_id == participant_id,
    )
    result = await db.execute(stmt)
    membership = result.scalars().first()
    if not membership:
        raise HTTPException(status_code=404, detail="Участник не найден в этом справочнике")
    await db.delete(membership)
    await db.commit()
    return None


@app.get("/directories/{directory_id}/members/", response_model=List[schemas.ParticipantRead])
async def list_directory_members(
    directory_id: int,
    query: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
):
    if not await db.get(models.Directory, directory_id):
        raise HTTPException(status_code=404, detail="Справочник не найден.")

    stmt = select(models.Participant).join(
        models.DirectoryMembership,
        models.Participant.id == models.DirectoryMembership.participant_id,
    ).filter(models.DirectoryMembership.directory_id == directory_id)

    if query:
        search_pattern = f"%{query}%"
        stmt = stmt.filter(
            (models.Participant.full_name.ilike(search_pattern))
            | (models.Participant.email.ilike(search_pattern))
            | (models.Participant.note.ilike(search_pattern))
        )

    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@app.post("/events/{event_id}/register/", response_model=List[schemas.RegistrationRead])
async def register_users(
    event_id: int,
    participant_ids: Optional[List[int]] = Body(None),
    directory_id: Optional[int] = Body(None),
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_registrar_or_admin),
):
    registered_by_user_id = current_user.id

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
            models.DirectoryMembership.directory_id == directory_id,
        )
        result_members = await db.execute(stmt_dir_members)
        target_participant_ids.update(result_members.scalars().all())

    if not target_participant_ids:
        raise HTTPException(status_code=400, detail="Не указаны участники.")

    stmt_existing = select(models.Registration.participant_id).filter(
        models.Registration.event_id == event_id,
        models.Registration.participant_id.in_(target_participant_ids),
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
            registered_by_user_id=registered_by_user_id,
        )
        db.add(db_registration)
        successful_registrations.append(db_registration)

    await db.commit()
    for reg in successful_registrations:
        await db.refresh(reg)
    return successful_registrations


@app.delete("/events/{event_id}/participants/{participant_id}", status_code=204)
async def unregister_participant(
    event_id: int,
    participant_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: models.SystemUser = Depends(get_current_admin),
):
    stmt = select(models.Registration).filter(
        models.Registration.event_id == event_id,
        models.Registration.participant_id == participant_id,
    )
    result = await db.execute(stmt)
    registration = result.scalars().first()
    if not registration:
        raise HTTPException(status_code=404, detail="Регистрация не найдена.")
    await db.delete(registration)
    await db.commit()
    return None


@app.get("/events/{event_id}/participants/", response_model=List[schemas.ParticipantStatus])
async def get_event_participants(
    event_id: int,
    query: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: models.SystemUser = Depends(get_current_registrar_or_admin),
):
    stmt = select(
        models.Participant,
        models.Registration.arrival_time,
        models.SystemUser.username.label("registered_by_full_name"),
        models.SystemUser.role.label("registered_by_role"),
    ).join(
        models.Registration,
        models.Participant.id == models.Registration.participant_id,
    ).join(
        models.SystemUser,
        models.Registration.registered_by_user_id == models.SystemUser.id,
    ).filter(
        models.Registration.event_id == event_id,
    )

    if query:
        search_pattern = f"%{query}%"
        stmt = stmt.filter(
            (models.Participant.full_name.ilike(search_pattern))
            | (models.Participant.email.ilike(search_pattern))
            | (models.Participant.note.ilike(search_pattern))
        )

    stmt = stmt.limit(limit)
    result = await db.execute(stmt)

    participants_status: list[schemas.ParticipantStatus] = []
    for participant_orm, arrival_time, reg_full_name, reg_role in result.all():
        participant_dict = schemas.ParticipantRead.from_orm(participant_orm).dict()
        participants_status.append(
            schemas.ParticipantStatus(
                **participant_dict,
                arrival_time=arrival_time,
                registered_by_full_name=reg_full_name,
                registered_by_role=reg_role,
            )
        )

    return participants_status
