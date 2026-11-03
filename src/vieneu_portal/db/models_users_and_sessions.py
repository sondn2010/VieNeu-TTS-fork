from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    BigInteger,
    String,
    Text,
    TIMESTAMP,
    func,
)
from sqlalchemy.dialects.postgresql import INET, UUID

from .base import Base


class User(Base):
    __tablename__ = "users"

    # -- spec 08 --
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    email = Column(String(255), nullable=False, unique=True)
    username = Column(String(100), nullable=False)
    avatar_initials = Column(String(4), nullable=False, server_default="US")
    plan_tier = Column(String(32), nullable=False, server_default="TRIAL")
    token_balance = Column(BigInteger, nullable=False, server_default="150000")
    token_quota_total = Column(BigInteger, nullable=False, server_default="150000")
    daily_char_limit = Column(Integer, nullable=False, server_default="50000")
    daily_char_remaining = Column(Integer, nullable=False, server_default="50000")
    plan_expires_at = Column(TIMESTAMP(timezone=True), nullable=True)
    has_desktop_license = Column(Boolean, nullable=False, server_default="false")
    has_accepted_tts_terms = Column(Boolean, nullable=False, server_default="false")
    terms_accepted_at = Column(TIMESTAMP(timezone=True), nullable=True)
    onboarding_completed_steps = Column(Integer, nullable=False, server_default="0")
    onboarding_hidden = Column(Boolean, nullable=False, server_default="false")
    ui_theme = Column(String(16), nullable=False, server_default="dark")
    ui_language = Column(String(8), nullable=False, server_default="vi")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # -- C0 additions: auth, roles, per-user synthesis lease, migration provenance --
    password_hash = Column(Text, nullable=False)
    role = Column(String(16), nullable=False, server_default="USER")
    is_active = Column(Boolean, nullable=False, server_default="true")
    last_login_at = Column(TIMESTAMP(timezone=True), nullable=True)
    terms_version = Column(String(16), nullable=True)
    terms_accepted_ip = Column(INET, nullable=True)
    daily_chars_reset_on = Column(Date, nullable=False, server_default=func.current_date())
    synthesis_lock_until = Column(TIMESTAMP(timezone=True), nullable=True)
    legacy_source_id = Column(Text, nullable=True, unique=True)

    __table_args__ = (
        CheckConstraint("role IN ('USER', 'ADMIN', 'SUPERADMIN')", name="ck_users_role"),
        Index("ix_users_email_lower", func.lower(email), unique=True),
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    token_hash = Column(Text, primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    csrf_nonce = Column(Text, nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    absolute_expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    ip = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_user_sessions_expires_at", "expires_at"),
        Index("ix_user_sessions_user_id", "user_id"),
    )
