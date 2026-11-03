from __future__ import annotations

from sqlalchemy import (
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from .base import Base


class Podcast(Base):
    __tablename__ = "podcasts"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=True)
    settings_json = Column(
        JSONB,
        nullable=False,
        server_default=text("'{\"pause_ms\": 400, \"normalize_lufs\": -16}'::jsonb"),
    )
    turn_count = Column(Integer, nullable=False, server_default="0")
    total_chars = Column(Integer, nullable=False, server_default="0")
    tokens_consumed = Column(Integer, nullable=False, server_default="0")
    duration_seconds = Column(Numeric(8, 1), nullable=True)
    audio_url = Column(Text, nullable=True)
    status = Column(String(24), nullable=False, server_default="DRAFT")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'PROCESSING', 'SUCCESS', 'FAILED')", name="ck_podcasts_status"
        ),
        Index("idx_podcasts_user_id", "user_id"),
    )


class PodcastTurn(Base):
    __tablename__ = "podcast_turns"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    podcast_id = Column(
        PGUUID(as_uuid=True), ForeignKey("podcasts.id", ondelete="CASCADE"), nullable=False
    )
    turn_order = Column(Integer, nullable=False)
    speaker_name = Column(String(100), nullable=False)
    voice_id = Column(String(64), ForeignKey("voices.id"), nullable=False)
    style = Column(String(64), nullable=False, server_default="Tự nhiên")
    content = Column(Text, nullable=False)
    turn_audio_url = Column(Text, nullable=True)
    duration_seconds = Column(Numeric(8, 1), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (Index("idx_podcast_turns_podcast_id", "podcast_id"),)


class StoryProject(Base):
    __tablename__ = "story_projects"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False, server_default="Truyện mới")
    model_version = Column(String(16), nullable=False, server_default="V4")
    segment_count = Column(Integer, nullable=False, server_default="0")
    merged_audio_url = Column(Text, nullable=True)
    total_duration_seconds = Column(Numeric(8, 1), nullable=True)
    last_exported_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (Index("idx_story_projects_user_id", "user_id"),)


class StoryCharacter(Base):
    __tablename__ = "story_characters"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    project_id = Column(
        PGUUID(as_uuid=True), ForeignKey("story_projects.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(100), nullable=False)
    voice_id = Column(String(64), ForeignKey("voices.id"), nullable=False)
    color_hex = Column(String(16), nullable=False, server_default="#7C5CFC")
    default_style = Column(String(64), nullable=False, server_default="Tự nhiên")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (Index("idx_story_characters_project_id", "project_id"),)


class StorySegment(Base):
    __tablename__ = "story_segments"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    project_id = Column(
        PGUUID(as_uuid=True), ForeignKey("story_projects.id", ondelete="CASCADE"), nullable=False
    )
    character_id = Column(PGUUID(as_uuid=True), ForeignKey("story_characters.id"), nullable=False)
    sort_order = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    audio_url = Column(Text, nullable=True)
    duration_seconds = Column(Numeric(8, 1), nullable=True)
    status = Column(String(32), nullable=False, server_default="DRAFT")
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'GENERATING', 'READY', 'MODIFIED_NEEDS_REGEN')",
            name="ck_story_segments_status",
        ),
        Index("idx_story_segments_project_id", "project_id"),
        Index("idx_story_segments_character_id", "character_id"),
    )
