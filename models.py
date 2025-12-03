from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from enum import Enum
from database import Base

class SystemUserRole(str, Enum):
    ADMIN = "Admin"
    OPERATOR = "Operator"
    REGISTRAR = "Registrar"
    PARTICIPANT = "Participant"

class SystemUser(Base):
    __tablename__ = "system_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    role: Mapped[str] = mapped_column(String)
    hashed_password: Mapped[str] = mapped_column(String)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_sync_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_date: Mapped[datetime] = mapped_column(DateTime)
    registration_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_participants: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)

    participants: Mapped[list["Participant"]] = relationship(
        "Participant",
        back_populates="event",
        cascade="all, delete-orphan",
    )
    logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="event",
        cascade="all, delete-orphan",
    )

class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("events.id"), index=True, nullable=True)
    full_name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, index=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    registration_date: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    is_checked_in: Mapped[bool] = mapped_column(Boolean, default=False)

    event: Mapped["Event | None"] = relationship("Event", back_populates="participants")
    
    directory_memberships: Mapped[list["DirectoryMembership"]] = relationship(
        "DirectoryMembership",
        back_populates="participant",
        cascade="all, delete-orphan",
    )

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

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(Integer, ForeignKey("events.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    action: Mapped[str] = mapped_column(String)
    user_id: Mapped[int] = mapped_column(Integer)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)

    event: Mapped["Event"] = relationship("Event", back_populates="logs")

class Directory(Base):
    __tablename__ = "directories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    memberships: Mapped[list["DirectoryMembership"]] = relationship(
        "DirectoryMembership",
        back_populates="directory",
        cascade="all, delete-orphan",
    )

class DirectoryMembership(Base):
    __tablename__ = "directory_memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    directory_id: Mapped[int] = mapped_column(Integer, ForeignKey("directories.id"))
    participant_id: Mapped[int] = mapped_column(Integer, ForeignKey("participants.id"))

    directory: Mapped["Directory"] = relationship("Directory", back_populates="memberships")
    participant: Mapped["Participant"] = relationship("Participant", back_populates="directory_memberships")
