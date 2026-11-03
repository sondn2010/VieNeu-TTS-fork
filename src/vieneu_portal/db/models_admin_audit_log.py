from __future__ import annotations

from sqlalchemy import BigInteger, Column, ForeignKey, Index, String, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from .base import Base


class AdminAuditLog(Base):
    """One row per admin mutation and per admin listing of another user's
    recordings (`user.recordings_view`). Kept forever; no purge job in C1.
    No FK on `target_id` so rows survive the target being deleted.
    """

    __tablename__ = "admin_audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    actor_user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_label = Column(String(255), nullable=False)
    action = Column(String(64), nullable=False)
    target_type = Column(String(32), nullable=False)
    target_id = Column(Text, nullable=False)
    target_label = Column(Text, nullable=True)
    before = Column(JSONB, nullable=True)
    after = Column(JSONB, nullable=True)
    ip = Column(INET, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_admin_audit_log_created_at", created_at.desc()),
        Index("idx_admin_audit_log_target", "target_type", "target_id"),
        Index("idx_admin_audit_log_actor_user_id", "actor_user_id"),
    )
