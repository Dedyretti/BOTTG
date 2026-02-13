from enum import Enum


class RoleEnum(str, Enum):
    """Enum для ролей пользователя"""

    USER = "user"
    ADMIN = "admin"
    SUPERUSER = "superuser"


class RequestTypeEnum(str, Enum):
    """Enum для статусов отгула"""

    DAY_OFF = "day_off"
    REMOTE = "remote"
    VACATION = "vacation"
    SICK_LEAVE = "sick_leave"
    PARTIAL_ABSENCE = "partial_absence"


class RequestStatusEnum(str, Enum):
    """Enum для статусов обработки заявок"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ChangeTypeEnum(str, Enum):
    """Enum для статусов обработки заявок"""

    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    COMMENT_UPDATED = "comment_updated"
    CANCELLED = "cancelled"
    COMMENT_ADDED = "comment_added"
