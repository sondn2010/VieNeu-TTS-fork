from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Computed,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from .base import Base


class PronunciationRule(Base):
    """Per-account dictionary (spec 08 `pronunciation_rules`)."""

    __tablename__ = "pronunciation_rules"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source_term = Column(String(255), nullable=False)
    phonetic_replacement = Column(String(255), nullable=False)
    match_whole_word = Column(Boolean, nullable=False, server_default="true")
    case_sensitive = Column(Boolean, nullable=False, server_default="false")
    is_enabled = Column(Boolean, nullable=False, server_default="true")
    sort_order = Column(Integer, nullable=False, server_default="0")
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (Index("idx_pronunciation_rules_user", "user_id", sort_order.asc()),)


class SystemDictionary(Base):
    """Admin-managed dictionary pack (math/chem seed rules, English fallback, ...)."""

    __tablename__ = "system_dictionaries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False, unique=True)
    kind = Column(String(32), nullable=False)
    is_enabled = Column(Boolean, nullable=False, server_default="true")
    description = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, server_default="0")
    legacy_source_id = Column(Text, nullable=True, unique=True)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class SystemPronunciationRule(Base):
    """Rule rows of a `SystemDictionary` pack: same shape as `PronunciationRule`
    plus `rule_kind` (`REPLACE` vs `ENGLISH_FALLBACK`) and a generated `term_key`
    mirroring the legacy account-rule uniqueness (case-sensitive source term, or
    its lowercase form).
    """

    __tablename__ = "system_pronunciation_rules"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    dictionary_id = Column(
        Integer, ForeignKey("system_dictionaries.id", ondelete="CASCADE"), nullable=False
    )
    source_term = Column(String(255), nullable=False)
    phonetic_replacement = Column(String(255), nullable=False, server_default="")
    match_whole_word = Column(Boolean, nullable=False, server_default="true")
    case_sensitive = Column(Boolean, nullable=False, server_default="false")
    is_enabled = Column(Boolean, nullable=False, server_default="true")
    sort_order = Column(Integer, nullable=False, server_default="0")
    note = Column(Text, nullable=False, server_default="")
    rule_kind = Column(String(16), nullable=False, server_default="REPLACE")
    term_key = Column(
        Text,
        Computed(
            "CASE WHEN case_sensitive THEN source_term ELSE lower(source_term) END",
            persisted=True,
        ),
    )
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "rule_kind IN ('REPLACE', 'ENGLISH_FALLBACK')",
            name="ck_system_pronunciation_rules_rule_kind",
        ),
        CheckConstraint(
            "rule_kind <> 'REPLACE' OR phonetic_replacement <> ''",
            name="ck_system_pronunciation_rules_replace_has_value",
        ),
        UniqueConstraint("dictionary_id", "term_key", name="uq_system_pronunciation_rules_dictionary_id_term_key"),
    )
