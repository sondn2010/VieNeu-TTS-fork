from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TIMESTAMP,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from .base import Base


class DeveloperApiKey(Base):
    __tablename__ = "developer_api_keys"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(150), nullable=False)
    environment = Column(String(16), nullable=False)
    key_prefix = Column(String(24), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    last_used_at = Column(TIMESTAMP(timezone=True), nullable=True)
    revoked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("environment IN ('LIVE', 'TEST')", name="ck_developer_api_keys_environment"),
        Index("idx_developer_api_keys_user_id", "user_id"),
    )


class McpConnectedClient(Base):
    __tablename__ = "mcp_connected_clients"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    client_name = Column(String(120), nullable=False)
    client_id = Column(String(255), nullable=False)
    connected_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    last_active_at = Column(TIMESTAMP(timezone=True), nullable=True)
    revoked_at = Column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (Index("idx_mcp_connected_clients_user_id", "user_id"),)


class Voucher(Base):
    __tablename__ = "vouchers"

    code = Column(String(64), primary_key=True)
    discount_percent = Column(Integer, nullable=False)
    applicable_plans = Column(ARRAY(Text), nullable=False)
    max_uses_per_user = Column(Integer, nullable=False, server_default="1")
    total_quota = Column(Integer, nullable=True)
    used_count = Column(Integer, nullable=False, server_default="0")
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")

    __table_args__ = (
        CheckConstraint(
            "discount_percent BETWEEN 1 AND 100", name="ck_vouchers_discount_percent"
        ),
    )
