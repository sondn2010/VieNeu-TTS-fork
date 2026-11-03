from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    TIMESTAMP,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from .base import Base


class Voice(Base):
    __tablename__ = "voices"

    # -- spec 08 --
    id = Column(String(64), primary_key=True)
    name = Column(String(120), nullable=False)
    initials = Column(String(4), nullable=False)
    avatar_url = Column(Text, nullable=True)
    gender = Column(String(16), nullable=False)
    region = Column(String(32), nullable=False)
    language_code = Column(String(16), nullable=False, server_default="vi-VN")
    language_label = Column(String(64), nullable=False, server_default="Tiếng Việt (VN)")
    model_version = Column(String(16), nullable=False, server_default="V4")
    tags = Column(ARRAY(Text), nullable=False, server_default=text("'{}'::text[]"))
    supported_styles = Column(
        ARRAY(Text), nullable=False, server_default=text("ARRAY['Tự nhiên']::text[]")
    )
    sample_audio_url = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # -- C0 additions: engine voice id, sync with engine catalog --
    engine_voice_name = Column(String(64), nullable=False)
    sort_order = Column(Integer, nullable=False, server_default="0")
    sample_object_key = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("gender IN ('NAM', 'NU')", name="ck_voices_gender"),
        CheckConstraint("region IN ('MIEN_BAC', 'MIEN_TRUNG', 'MIEN_NAM')", name="ck_voices_region"),
    )


class TTSRecording(Base):
    __tablename__ = "tts_recordings"

    # -- spec 08 --
    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    voice_id = Column(String(64), ForeignKey("voices.id"), nullable=False)
    model_version = Column(String(16), nullable=False, server_default="V4")
    original_text = Column(Text, nullable=False)
    processed_text = Column(Text, nullable=True)
    speed = Column(Numeric(3, 2), nullable=False, server_default="1.00")
    bg_music_id = Column(String(64), nullable=True)
    char_count = Column(Integer, nullable=False)
    tokens_consumed = Column(Integer, nullable=False)
    duration_seconds = Column(Numeric(8, 1), nullable=False, server_default="0.0")
    audio_url = Column(Text, nullable=True)
    status = Column(String(24), nullable=False, server_default="SUCCESS")
    error_code = Column(String(64), nullable=True)
    source_module = Column(String(32), nullable=False, server_default="STUDIO")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # -- C0 additions: object storage key, async render queue (the row is the queue item) --
    audio_object_key = Column(Text, nullable=True)
    render_mode = Column(String(8), nullable=False, server_default="SYNC")
    attempts = Column(Integer, nullable=False, server_default="0")
    locked_until = Column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'SUCCESS', 'FAILED')", name="ck_tts_recordings_status"),
        CheckConstraint(
            "source_module IN ('STUDIO', 'PODCAST', 'STORY', 'API', 'MCP')",
            name="ck_tts_recordings_source_module",
        ),
        CheckConstraint("render_mode IN ('SYNC', 'ASYNC')", name="ck_tts_recordings_render_mode"),
        Index("idx_tts_recordings_user_created", "user_id", created_at.desc()),
        Index("idx_tts_recordings_voice_created", "voice_id", created_at.desc()),
        Index(
            "idx_tts_recordings_pending_async",
            created_at,
            postgresql_where=text("status = 'PENDING' AND render_mode = 'ASYNC'"),
        ),
        Index(
            "idx_tts_recordings_text_trgm",
            original_text,
            postgresql_using="gin",
            postgresql_ops={"original_text": "gin_trgm_ops"},
        ),
    )
