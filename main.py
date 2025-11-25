from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Dict, Any, Optional
from datetime import datetime, date # Добавили date для гибкости

# ------------------------------------
# --- Pydantic Модели Данных (Схемы) ---
# ------------------------------------

# --- Пользователь (User) ---

# Модель для создания пользователя (ФИО и Примечание)
class UserCreate(BaseModel):
    full_name: str
    # В задаче указано, что примечание может быть пустым
    note: Optional[str] = None 
    # Добавим email для демонстрации EmailStr
    email: EmailStr 
    
class UserRead(UserCreate):
    """Схема для чтения (с ID)"""
    id: int

# --- Мероприятие (Event) ---

class EventCreate(BaseModel):
    title: str
    date: date # Используем date, если время не критично, или datetime
    # Согласно задаче: статус регистрации активно или не активно.
    registration_active: bool = True
    max_capacity: Optional[int] = None # Максимальное количество участников
    
class EventRead(EventCreate):
    """Схема для чтения (с ID)"""
    id: int

# --- Регистрация / Участник (Registration) ---

class RegistrationBase(BaseModel):
    event_id: int
    user_id: int
    # Поле время, которое будем заполнять, если он придет (может быть пустым)
    arrival_time: Optional[datetime] = None 

class RegistrationRead(RegistrationBase):
    """Схема для чтения (с ID)"""
    id: int

class ParticipantStatus(UserRead):
    """Схема для вывода списка участников мероприятия"""
    # Добавляем поле из регистрации, но включаем его в схему User
    arrival_time: Optional[datetime] = None


# ----------------------------------------
# --- Временное Хранилище Данных (DB) ---
# ----------------------------------------
# Используем List[Dict] для имитации изменяемой БД в памяти.

db_users: List[Dict] = []
db_events: List[Dict] = []
db_registrations: List[Dict] = [] 

next_user_id = 1
next_event_id = 1
next_registration_id = 1


# ----------------------------------
# --- Приложение FastAPI ---
# ----------------------------------

app = FastAPI(
    title="Event Registration API",
    description="API for managing users and event registrations.",
    version="1.0.0"
)

# --------------------------
# --- Маршруты (Endpoints) ---
# --------------------------

@app.get("/")
def read_root():
    return {"message": "Welcome to the Event Registration API!"}

# --------------------------
# 1. МАРШРУТЫ ПОЛЬЗОВАТЕЛЕЙ
# --------------------------

@app.post("/users/", response_model=UserRead)
def create_user(user: UserCreate):
    """
    Создает нового пользователя. ФИО + Примечание должны быть уникальны.
    """
    global next_user_id
    
    # 1. Проверка уникальности (ФИО + Примечание)
    for existing_user in db_users:
        if (existing_user["full_name"] == user.full_name and 
            existing_user.get("note") == user.note):
            
            raise HTTPException(
                status_code=400, 
                detail="User with this Full Name and Note combination already exists."
            )
    
    # 2. Имитация сохранения в БД
    user_data = user.dict()
    user_data["id"] = next_user_id
    next_user_id += 1
    
    db_users.append(user_data)
    
    return user_data

@app.get("/users/", response_model=List[UserRead])
def read_users():
    """Возвращает список всех зарегистрированных пользователей."""
    return db_users

# --------------------------
# 2. МАРШРУТЫ МЕРОПРИЯТИЙ
# --------------------------

@app.post("/events/", response_model=EventRead)
def create_event(event: EventCreate):
    """Создает новое мероприятие."""
    global next_event_id
    
    # Имитация сохранения в БД
    event_data = event.dict()
    event_data["id"] = next_event_id
    next_event_id += 1
    
    db_events.append(event_data)
    
    return event_data

# --------------------------
# 3. МАРШРУТЫ РЕГИСТРАЦИИ
# --------------------------

@app.post("/events/{event_id}/register/", response_model=RegistrationRead)
def register_user(event_id: int, registration_data: RegistrationBase):
    """
    Регистрирует пользователя на мероприятие. 
    Проверяет активность регистрации и наличие дубликатов.
    """
    global next_registration_id

    # Проверка Event и User
    event = next((e for e in db_events if e["id"] == event_id), None)
    user = next((u for u in db_users if u["id"] == registration_data.user_id), None)
    
    if not event:
        raise HTTPException(status_code=404, detail=f"Event with id {event_id} not found.")
    if not user:
        raise HTTPException(status_code=404, detail=f"User with id {registration_data.user_id} not found.")

    # Проверка статуса регистрации
    if not event.get("registration_active"):
        raise HTTPException(status_code=403, detail=f"Registration for event {event_id} is currently inactive.")
    
    # Проверка на дубликат регистрации
    is_already_registered = any(
        r["event_id"] == event_id and r["user_id"] == registration_data.user_id
        for r in db_registrations
    )
    if is_already_registered:
        raise HTTPException(status_code=400, detail="User is already registered for this event.")

    # Сохранение регистрации
    reg_data = registration_data.dict()
    reg_data["id"] = next_registration_id
    next_registration_id += 1
    
    db_registrations.append(reg_data)
    
    return reg_data

@app.post("/events/{event_id}/checkin/{user_id}", response_model=RegistrationRead)
def checkin_user(event_id: int, user_id: int):
    """
    Отмечает явку пользователя на мероприятие (заполняет arrival_time).
    """
    
    # 1. Поиск регистрации
    registration = next(
        (r for r in db_registrations if r["event_id"] == event_id and r["user_id"] == user_id),
        None
    )
    
    if not registration:
        raise HTTPException(status_code=404, detail="Registration not found for this user/event.")

    # 2. Проверка, был ли пользователь уже отмечен
    if registration.get("arrival_time") is not None:
        raise HTTPException(status_code=400, detail="User has already been checked in.")

    # 3. Обновление времени явки
    now = datetime.now()
    # Сохраняем в формате, который может быть легко сериализован/десериализован
    registration["arrival_time"] = now.isoformat() 
    
    # Возвращаем обновленную запись (нужно преобразовать строку обратно в datetime для Pydantic)
    registration_for_return = RegistrationRead(
        id=registration["id"],
        event_id=registration["event_id"],
        user_id=registration["user_id"],
        arrival_time=now # Передаем объект datetime
    )
    return registration_for_return
    
@app.get("/events/{event_id}/participants/", response_model=List[ParticipantStatus])
def get_event_participants(event_id: int):
    """
    Получает список всех участников мероприятия с их статусом явки.
    """
    
    if not next((e for e in db_events if e["id"] == event_id), None):
        raise HTTPException(status_code=404, detail=f"Event with id {event_id} not found.")

    # 1. Фильтруем регистрации по event_id
    event_registrations = [
        r for r in db_registrations if r["event_id"] == event_id
    ]
    
    participants = []
    
    for reg in event_registrations:
        # 2. Находим данные пользователя
        user_data = next((u for u in db_users if u["id"] == reg["user_id"]), None)
        
        if user_data:
            # 3. Объединяем данные пользователя и статус явки
            participant_info = {
                "id": user_data["id"],
                "full_name": user_data["full_name"],
                "note": user_data.get("note"),
                "email": user_data.get("email"),
                # Значение arrival_time берем из регистрации
                "arrival_time": reg.get("arrival_time") 
            }
            participants.append(participant_info)
            
    return participants