from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, UniqueConstraint, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

# Импортируем Base из database.py
from database import Base 

# --- Новое: Enum для ролей системных пользователей ---
class SystemUserRole(enum.Enum):
    """Определяет роли для сотрудников системы."""
    ADMIN = "admin"
    REGISTRAR = "registrar"

# ----------------------------------------------------
# 1. PARTICIPANT (Ранее User) - Участник мероприятия
# ----------------------------------------------------
class Participant(Base):
    """
    Модель для участника мероприятия (того, кто регистрируется).
    Ранее называлась User.
    """
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone = Column(String, nullable=True)
    note = Column(String, nullable=True)

    # Отношение к регистрации
    registrations = relationship("Registration", back_populates="participant")
    
    # Отношение к членству в справочниках
    directory_memberships = relationship("DirectoryMembership", back_populates="participant")

    # Уникальность по ФИО и Примечанию (для идентификации похожих людей)
    __table_args__ = (
        UniqueConstraint('full_name', 'note', name='uc_full_name_note'),
    )

# ----------------------------------------------------
# 2. SYSTEM USER - Администраторы и Регистраторы
# ----------------------------------------------------
class SystemUser(Base):
    """
    Модель для системных пользователей (Администраторы и Регистраторы).
    """
    __tablename__ = "system_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String)
    # Используем Enum для ролей
    role = Column(Enum(SystemUserRole), default=SystemUserRole.REGISTRAR, nullable=False)
    
    # Пока не добавляем пароль, но его нужно будет добавить для реальной системы
    # hashed_password = Column(String) 

    # Обратное отношение к регистрации (те, кого зарегистрировал этот сотрудник)
    registrations_made = relationship("Registration", back_populates="registered_by")


# ----------------------------------------------------
# 3. EVENT - Мероприятие
# ----------------------------------------------------
class Event(Base):
    """Модель для мероприятия."""
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    event_date = Column(DateTime)
    registration_active = Column(Boolean, default=True)

    # Отношение к регистрации
    registrations = relationship("Registration", back_populates="event")

# ----------------------------------------------------
# 4. DIRECTORY - Справочник (Группы участников)
# ----------------------------------------------------
class Directory(Base):
    """
    Справочник или группа участников (например, "Анабарский улус").
    """
    __tablename__ = "directories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)

    memberships = relationship("DirectoryMembership", back_populates="directory")

# ----------------------------------------------------
# 5. DIRECTORY MEMBERSHIP - Связь Участник <-> Справочник
# ----------------------------------------------------
class DirectoryMembership(Base):
    """
    Модель связи многие-ко-многим: Участник в Справочнике.
    """
    __tablename__ = "directory_memberships"

    participant_id = Column(Integer, ForeignKey("participants.id"), primary_key=True)
    directory_id = Column(Integer, ForeignKey("directories.id"), primary_key=True)
    
    # Уникальность по паре (participant_id, directory_id) обеспечивается первичным ключом

    participant = relationship("Participant", back_populates="directory_memberships")
    directory = relationship("Directory", back_populates="memberships")


# ----------------------------------------------------
# 6. REGISTRATION - Регистрация участника на мероприятие
# ----------------------------------------------------
class Registration(Base):
    """Модель для регистрации участника на мероприятие."""
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), index=True)
    participant_id = Column(Integer, ForeignKey("participants.id"), index=True) # Использование participant_id
    
    # Новое поле: ID системного пользователя, который провел регистрацию
    registered_by_user_id = Column(Integer, ForeignKey("system_users.id"), index=True, nullable=False) 

    registration_time = Column(DateTime, default=datetime.now)
    arrival_time = Column(DateTime, nullable=True)

    # Отношения
    event = relationship("Event", back_populates="registrations")
    participant = relationship("Participant", back_populates="registrations")
    # Отношение к сотруднику, который зарегистрировал
    registered_by = relationship("SystemUser", back_populates="registrations_made") 

    __table_args__ = (
        UniqueConstraint('event_id', 'participant_id', name='uc_event_participant'),
    )