import enum
from enum import Enum


class RoleEnum(str, Enum):
    USER = "user"
    ADMIN = "admin"
    SUPERUSER = "superuser"


class RequestTypeEnum(str, Enum):
    DAY_OFF = "day_off"
    REMOTE = "remote"
    VACATION = "vacation"
    SICK_LEAVE = "sick_leave"
    PARTIAL_ABSENCE = "partial_absence"


class RequestStatusEnum(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ChangeTypeEnum(str, Enum):
    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    COMMENT_UPDATED = "comment_updated"
    CANCELLED = "cancelled"
