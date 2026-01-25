from datetime import datetime, timedelta
from enum import Enum
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import  relationship




class Base(DeclarativeBase):
    pass


class RoleEnum(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPERUSER = "superuser"


class RequestTypeEnum(str, Enum):
    DAY_OFF = "day_off"                    # Отгул
    REMOTE = "remote"                      # Удаленная работа
    VACATION = "vacation"                  # Отпуск
    SICK_LEAVE = "sick_leave"              # Больничный
    PARTIAL_ABSENCE = "partial_absence"  # Частичное отсутствие


class RequestStatusEnum(str, Enum):
    PENDING = "pending"      # На рассмотрении
    APPROVED = "approved"    # Одобрено
    REJECTED = "rejected"    # Отклонено
    CANCELLED = "cancelled"  # Отменено


class ChangeTypeEnum(str, Enum):
    CREATED = "created"  # Создание
    STATUS_CHANGED = "status_changed"  # Изменение статуса
    COMMENT_UPDATED = "comment_updated"  # Обновление комментария
    CANCELLED = "cancelled"  # Отмена


class Person(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=True, index=True)
    name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)  
    patronymic = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    position = Column(String(200))
    role = Column(SQLEnum(RoleEnum), default=RoleEnum.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Связи
    invite_codes = relationship("InviteCode", back_populates="employee")
    requests = relationship("Request", back_populates="employee")
    created_invites = relationship(
        "InviteCode", foreign_keys="[InviteCode.created_by]", back_populates="creator"
    )
    request_history = relationship(
        "RequestHistory",
        foreign_keys="[RequestHistory.changed_by]",
        back_populates="changer",
    )
    admin_notifications = relationship("AdminNotification", back_populates="admin")


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    created_by = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    expires_at = Column(DateTime, default=lambda: datetime.now, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)  
    used_at = Column(DateTime, nullable=True) 

    # Связи
    employee = relationship(
        "Person", foreign_keys=[employee_id], back_populates="invite_codes"
    )
    creator = relationship(
        "Person", foreign_keys=[created_by], back_populates="created_invites"
    )

    # Индекс быстрого поиска активных кодов
    __table_args__ = (Index("idx_invite_code_active", "code", "is_used", "expires_at"),)


class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    request_type = Column(SQLEnum(RequestTypeEnum), nullable=False)
    start_date = Column(Date, nullable=False)  
    end_date = Column(Date, nullable=False)  
    comment = Column(Text)  
    status = Column(
        SQLEnum(RequestStatusEnum), default=RequestStatusEnum.PENDING, nullable=False
    )
    rejected_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Связи
    employee = relationship("Person", back_populates="requests")
    history = relationship("RequestHistory", back_populates="request")
    notifications = relationship("AdminNotification", back_populates="request")

    # Индексы
    __table_args__ = (
        Index("idx_request_status", "status"),
        Index("idx_request_dates", "start_date", "end_date"),
        Index("idx_request_employee_dates", "employee_id", "start_date", "end_date"),
    )


class RequestHistory(Base):
    __tablename__ = "request_history"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(
        Integer, ForeignKey("requests.id", ondelete="CASCADE"), nullable=False
    )
    changed_by = Column(
        Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=False
    )
    change_type = Column(SQLEnum(ChangeTypeEnum), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)  
    changed_at = Column(DateTime, default=datetime.now, nullable=False)
    reason = Column(Text)

    # Связи
    request = relationship("Request", back_populates="history")
    changer = relationship("Person", back_populates="request_history")

    # Индексы быстрого поиска по заявке
    __table_args__ = (
        Index("idx_history_request", "request_id", "changed_at"),
        Index("idx_history_type", "change_type", "changed_at"),
    )


class AdminNotification(Base):
    __tablename__ = "admin_notifications"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id", ondelete="CASCADE"), nullable=False)
    admin_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    message_id = Column(Integer, nullable=False)  # ID сообщения в Telegram
    chat_id = Column(Integer, nullable=False)  # ID чата в Telegram
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)  

    # Связи
    request = relationship("Request", back_populates="notifications")
    admin = relationship("Person", back_populates="admin_notifications")

    # Индекс для быстрого поиска активных уведомлений
    __table_args__ = (
        Index("idx_notification_active", "admin_id", "is_active", "created_at"),
        )
