from datetime import date, datetime, timedelta
import uuid

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    UUID as DB_UUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Employee(Base):
    """Сотрудник компании."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    telegram_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    patronymic: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    position: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    invite_codes: Mapped[list["InviteCode"]] = relationship(
        back_populates="employee",
        foreign_keys="[InviteCode.employee_id]",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    created_invites: Mapped[list["InviteCode"]] = relationship(
        foreign_keys="[InviteCode.created_by]",
        back_populates="creator",
        lazy="selectin"
    )
    absence_requests: Mapped[list["AbsenceRequest"]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    request_changes: Mapped[list["AbsenceRequestHistory"]] = relationship(
        foreign_keys="[AbsenceRequestHistory.changed_by]",
        back_populates="changer"
    )
    notifications: Mapped[list["AdminNotification"]] = relationship(
        back_populates="admin", cascade="all, delete-orphan"
    )


class InviteCode(Base):
    """Инвайт-код для привязки Telegram."""

    __tablename__ = "invite_codes"
    __table_args__ = (
        Index("idx_invite_code_active", "code", "is_used", "expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[uuid.UUID] = mapped_column(
        DB_UUID(as_uuid=True),
        unique=True,
        default=uuid.uuid4,
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE")
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now() + timedelta(days=1),
    )
    is_used: Mapped[bool] = mapped_column(default=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    employee: Mapped["Employee"] = relationship(
        foreign_keys=[employee_id], back_populates="invite_codes"
    )
    creator: Mapped["Employee | None"] = relationship(
        foreign_keys=[created_by], back_populates="created_invites"
    )


class AbsenceRequest(Base):
    """Заявка на отсутствие."""

    __tablename__ = "absence_requests"
    __table_args__ = (
        Index("idx_absence_request_status", "status"),
        Index("idx_absence_request_dates", "start_date", "end_date"),
        Index(
            "idx_absence_request_employee_dates",
            "employee_id",
            "start_date",
            "end_date",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE")
    )
    request_type: Mapped[str] = mapped_column(String(50))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    comment: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50))
    rejected_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    employee: Mapped["Employee"] = relationship(
        back_populates="absence_requests"
    )
    history: Mapped[list["AbsenceRequestHistory"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["AdminNotification"]] = relationship(
        back_populates="request", cascade="all, delete-orphan"
    )


class AbsenceRequestHistory(Base):
    """История изменений заявки."""

    __tablename__ = "absence_request_history"
    __table_args__ = (
        Index(
            "idx_absence_request_history_request",
            "request_id",
            "changed_at",
        ),
        Index("idx_absence_request_history_type", "change_type", "changed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("absence_requests.id", ondelete="CASCADE")
    )
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL")
    )
    change_type: Mapped[str] = mapped_column(String(50))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    reason: Mapped[str | None] = mapped_column(Text)

    request: Mapped["AbsenceRequest"] = relationship(back_populates="history")
    changer: Mapped["Employee | None"] = relationship(
        back_populates="request_changes"
    )


class AdminNotification(Base):
    """Уведомление админу в Telegram."""

    __tablename__ = "admin_notifications"
    __table_args__ = (
        Index(
            "idx_notification_active",
            "admin_id",
            "is_active",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("absence_requests.id", ondelete="CASCADE")
    )
    admin_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE")
    )
    message_id: Mapped[int] = mapped_column(BigInteger)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(default=True)

    request: Mapped["AbsenceRequest"] = relationship(
        back_populates="notifications"
    )
    admin: Mapped["Employee"] = relationship(back_populates="notifications")
