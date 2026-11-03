"""The migration's JSON report: per-table counts, the conflict list, and
`lost_rows` from the post-write set-equality verification. `exit_code()` is
0 only when `lost_rows == 0` and `conflicts == []`.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class Conflict:
    kind: str   # 'user_email' | 'dictionary_name'
    natural_key: str
    legacy_source_id: str
    existing_row_description: str


@dataclass
class MigrationReport:
    sqlite_path: str
    mode: str   # 'dry-run' | 'apply'
    users_total: int = 0
    users_inserted: int = 0
    users_skipped_existing: int = 0
    api_keys_total: int = 0
    api_keys_inserted: int = 0
    api_keys_skipped_existing: int = 0
    dictionaries_total: int = 0
    dictionaries_inserted: int = 0
    dictionaries_skipped_existing: int = 0
    rules_total: int = 0
    rules_inserted: int = 0
    sessions_counted_not_migrated: int = 0
    needs_email: list = field(default_factory=list)   # [{"username", "email"}, ...]
    conflicts: list = field(default_factory=list)      # list[Conflict]
    lost_rows: int = 0
    backup_path: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2, default=str)

    def exit_code(self) -> int:
        return 0 if self.lost_rows == 0 and not self.conflicts else 1
