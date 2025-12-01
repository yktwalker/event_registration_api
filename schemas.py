from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime
from models import SystemUserRole

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class SystemUserBase(BaseModel):
    username: str
    full_name: Optional[str] = None
    role: SystemUserRole = SystemUserRole.REGISTRAR

class SystemUserCreate(SystemUserBase):
    password: str

class SystemUserUpdate(BaseModel):
    """Схема для обновления данных пользователя (для Админа)."""
    full_name: Optional[str] = None
    role: Optional[SystemUserRole] = None
    password: Optional[str] = None

class SystemUserRead(SystemUserBase):
    id: int
    last_sync_time: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class ParticipantBase(BaseModel):
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    note: Optional[str] = None

class ParticipantCreate(ParticipantBase):
    pass

class ParticipantRead(ParticipantBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    event_date: datetime
    registration_active: bool = True

class EventCreate(EventBase):
    pass

class EventRead(EventBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class DirectoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class DirectoryCreate(DirectoryBase):
    pass

class DirectoryRead(DirectoryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class DirectoryMembershipCreate(BaseModel):
    participant_id: int
    directory_id: int
    model_config = ConfigDict(from_attributes=True)

class RegistrationBase(BaseModel):
    participant_id: int
    registered_by_user_id: int

class RegistrationCreate(RegistrationBase):
    pass

class RegistrationRead(RegistrationBase):
    id: int
    event_id: int
    registration_time: datetime
    arrival_time: Optional[datetime] = None
    registered_by: Optional[SystemUserRead] = None
    
    model_config = ConfigDict(from_attributes=True)

class ParticipantStatus(ParticipantRead):
    arrival_time: Optional[datetime] = None
    registered_by_full_name: str
    registered_by_role: SystemUserRole
    
    model_config = ConfigDict(from_attributes=True)

# --- Схемы для синхронизации ---

class SyncRequest(BaseModel):
    last_sync_time: Optional[datetime] = None
    known_registration_ids: Optional[List[int]] = None

class SyncResponse(BaseModel):
    new_registrations: List[RegistrationRead]
    server_time: datetime
