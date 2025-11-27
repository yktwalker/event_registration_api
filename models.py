from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from enum import Enum 

# Импортируем Base из database.py
from database import Base

# --- Перечисление ролей пользователя ---
class SystemUserRole(str, Enum):
    ADMIN = "Admin"
    REGISTRAR = "Registrar"
    PARTICIPANT = "Participant"

# ----------------------------------------------------
# --- Модель системного пользователя (для RBAC/Аутентификации) ---
class SystemUser(Base):
    __tablename__ = "system_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    
    # 'Admin', 'Registrar'
    role: Mapped[str] = mapped_column(String) 
    
    # Добавлено для JWT: Хешированный пароль
    hashed_password: Mapped[str] = mapped_column(String)
    
    # Опциональное поле для полного имени, используется в schemas
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)

# --- Модель события ---
class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True)
    event_date: Mapped[datetime] = mapped_column(DateTime)
    registration_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_participants: Mapped[int] = mapped_column(Integer, default=None, nullable=True)

    # Связь с участниками
    participants: Mapped[list["Participant"]] = relationship(
        "Participant",
        back_populates="event",
        cascade="all, delete-orphan"
    )
    
    # Связь с логами
    logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="event",
        cascade="all, delete-orphan"
    )

# --- Модель участника ---
class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id"), index=True)
    full_name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, index=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    registration_date: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_checked_in: Mapped[bool] = mapped_column(Boolean, default=False)

    event: Mapped["Event"] = relationship("Event", back_populates="participants")
    
    directory_memberships: Mapped[list["DirectoryMembership"]] = relationship(
        "DirectoryMembership",
        back_populates="participant",
        cascade="all, delete-orphan"
    )

# --- Модель регистрации (Registration) ---
class Registration(Base):
    __tablename__ = "registrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id"))
    participant_id: Mapped[int] = mapped_column(Integer, ForeignKey("participants.id"))
    registered_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_users.id"))
    
    registration_time: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    arrival_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    event: Mapped["Event"] = relationship("Event")
    participant: Mapped["Participant"] = relationship("Participant")
    registered_by: Mapped["SystemUser"] = relationship("SystemUser")

# --- Модель Журнала действий (Audit Log) ---
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    action: Mapped[str] = mapped_column(String) 
    user_id: Mapped[int] = mapped_column(Integer) 
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    event: Mapped["Event"] = relationship("Event", back_populates="logs")

# --- Модель Справочника (Directory) ---
class Directory(Base):
    __tablename__ = "directories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    memberships: Mapped[list["DirectoryMembership"]] = relationship(
        "DirectoryMembership",
        back_populates="directory",
        cascade="all, delete-orphan"
    )

# --- Модель Членства в Справочнике ---
class DirectoryMembership(Base):
    __tablename__ = "directory_memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    directory_id: Mapped[int] = mapped_column(Integer, ForeignKey("directories.id"))
    participant_id: Mapped[int] = mapped_column(Integer, ForeignKey("participants.id"))

    directory: Mapped["Directory"] = relationship("Directory", back_populates="memberships")
    participant: Mapped["Participant"] = relationship("Participant", back_populates="directory_memberships")
