from __future__ import annotations

from sqlalchemy import BigInteger, CheckConstraint, Column, Index, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import INET

from .base import Base


class AuthThrottleEvent(Base):
    """Shared-across-processes login/signup throttle counter, replacing the old
    in-memory limiter. Rows older than 1 day are purged by the worker loop.
    """

    __tablename__ = "auth_throttle_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    kind = Column(Text, nullable=False)
    email_key = Column(Text, nullable=True)
    ip = Column(INET, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("kind IN ('LOGIN_FAILURE', 'SIGNUP')", name="ck_auth_throttle_events_kind"),
        Index("idx_auth_throttle_events_kind_ip_created", "kind", "ip", "created_at"),
        Index("idx_auth_throttle_events_kind_email_created", "kind", "email_key", "created_at"),
    )
