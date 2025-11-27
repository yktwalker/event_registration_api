from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from models import SystemUserRole # Импортируем Enum для ролей из models

# --- СХЕМЫ СИСТЕМНЫХ ПОЛЬЗОВАТЕЛЕЙ (Admin/Registrar) ---
class SystemUserBase(BaseModel):
    """Базовая схема для системного пользователя."""
    username: str
    full_name: str
    # Позволяем задать роль при создании, по умолчанию Registrar
    role: SystemUserRole = SystemUserRole.REGISTRAR

class SystemUserCreate(SystemUserBase):
    """Схема для создания нового системного пользователя."""
    # В идеале, здесь также должно быть поле 'password: str'
    pass

class SystemUserRead(SystemUserBase):
    """Схема для чтения системного пользователя."""
    id: int
    
    class Config:
        # Позволяет Pydantic читать данные из ORM-моделей (например, SystemUser)
        from_attributes = True

# --- СХЕМЫ УЧАСТНИКОВ (Participant) ---
class ParticipantBase(BaseModel):
    """Базовая схема для участника."""
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    note: Optional[str] = None

class ParticipantCreate(ParticipantBase):
    """Схема для создания нового участника."""
    pass

class ParticipantRead(ParticipantBase):
    """Схема для чтения участника."""
    id: int
    
    class Config:
        from_attributes = True

# --- СХЕМЫ МЕРОПРИЯТИЙ (Event) ---
class EventBase(BaseModel):
    """Базовая схема для мероприятия."""
    title: str
    description: Optional[str] = None
    event_date: datetime
    registration_active: bool = True

class EventCreate(EventBase):
    """Схема для создания нового мероприятия."""
    pass

class EventRead(EventBase):
    """Схема для чтения мероприятия."""
    id: int
    
    class Config:
        from_attributes = True

# --- СХЕМЫ СПРАВОЧНИКОВ (Directory) ---
class DirectoryBase(BaseModel):
    """Базовая схема для справочника/группы."""
    name: str
    description: Optional[str] = None

class DirectoryCreate(DirectoryBase):
    """Схема для создания нового справочника."""
    pass

class DirectoryRead(DirectoryBase):
    """Схема для чтения справочника."""
    id: int
    
    class Config:
        from_attributes = True

class DirectoryMembershipCreate(BaseModel):
    """Схема для добавления участника в справочник."""
    participant_id: int
    directory_id: int
    
    class Config:
        from_attributes = True

# --- СХЕМЫ РЕГИСТРАЦИИ (Registration) ---
class RegistrationBase(BaseModel):
    """Базовая схема для регистрации."""
    participant_id: int
    # ID сотрудника, который проводит регистрацию.
    registered_by_user_id: int 

class RegistrationCreate(RegistrationBase):
    """Схема для создания регистрации (используется в теле запроса)."""
    pass

class RegistrationRead(RegistrationBase):
    """Схема для чтения регистрации (возвращается API)."""
    id: int
    event_id: int
    registration_time: datetime
    arrival_time: Optional[datetime] = None
    
    # Добавляем связанные данные о регистраторе
    registered_by: Optional[SystemUserRead] = None 

    class Config:
        from_attributes = True

# --- СХЕМЫ СТАТУСА УЧАСТНИКА ---
class ParticipantStatus(ParticipantRead):
    """Схема для вывода списка участников с их статусом явки."""
    arrival_time: Optional[datetime] = None
    
    # Информация о сотруднике, который зарегистрировал участника
    registered_by_full_name: str
    registered_by_role: SystemUserRole
    
    class Config:
        from_attributes = True