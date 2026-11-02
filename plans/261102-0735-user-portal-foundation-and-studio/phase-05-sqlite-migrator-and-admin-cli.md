# Phase 05: SQLite -> Postgres migrator, system dictionary layer, admin services and CLI

## Context
- Source schema: `src/vieneu_admin/db.py:27-70` (users int id/username/scrypt hash/role admin|user/active; api_keys prefix+sha256; sessions; dictionaries kind english/term/name; dictionary_entries term/replacement/mode phonetic|en/case_sensitive/note; meta).
- SQLite online backup pattern: `src/vieneu_admin/db.py:144-159`. Old CLI to replace: `src/vieneu_admin/cli.py:28-88`.
- Dictionary JSON format `vieneu-dictionary/1`: `src/vieneu_preprocess/dictionary_schema.py:60-129`; `mode=en` ignores `replacement` (`src/vieneu_preprocess/types.py:12-17`).
- Seed packs: `src/vieneu_admin/seed/*.json` (7 files, 848 entries: term/phonetic 316, english/en 273, name/phonetic 130, term/en 125, name/en 4).
- Engine understands `<en>...</en>` (`src/vieneu_utils/core_utils.py:14-21`).

## Overview
Priority P1. Lossless one-time import of users, API keys and global dictionaries; seed packs become the system dictionary layer; admin service functions (shared by this CLI and the phase 13 API, DRY) with audit logging; minimal CLI for headless setups. Backups precede every write.

## Key insights
- SQLite users have no email: a username that is a valid email is used as is, otherwise `<username>@<--email-domain>` (default `migrated.invalid`), listed in the report as `needs_email`; admins fix it in the admin UI.
- Old role `admin` -> `SUPERADMIN` (it had full power), `user` -> `USER`. Hashes copy verbatim (same formats as phase 2).
- `<en>` entries (user decision, interpretation to confirm): `mode=en` with non-empty replacement -> normal `REPLACE` rule; `mode=en` with empty replacement -> `ENGLISH_FALLBACK` rule (matched text wrapped in `<en>...</en>`, lowest tie priority). All 402 seed `en` entries have empty replacement, so they become the fallback list. Export maps back (`ENGLISH_FALLBACK` -> `mode: "en"`), so JSON round-trips.
- Idempotent by natural keys: users `lower(email)`, keys `key_hash`, dictionaries `name`, rules `(dictionary_id, source_term, case_sensitive)`.

## Requirements
Admin services (`src/vieneu_portal/admin_services/`), each mutation writes one `admin_audit_log` row in the same transaction:
- `create_admin_user`, `reset_password` (revokes sessions), `set_user_active` (revokes sessions on disable), `set_user_role` with guards: cannot remove/disable/delete the last active SUPERADMIN (`409 LAST_SUPERADMIN`), cannot change own role or disable/delete self (`409 SELF_MODIFICATION`). Guard query locks SUPERADMIN rows (`FOR UPDATE`) to avoid two concurrent demotions both passing.
- System dictionary store: pack CRUD, rule list/replace-all, JSON import (`new|merge|replace`) and export, `.txt/.csv` import into a pack via the phase 7 parser.
- `write_admin_audit(actor, action, target, before, after, ip)`; CLI actor label `cli:<os-user>`.

CLI `python -m vieneu_portal <group> <command>`:
| Command | Behavior |
|---|---|
| `migrate-sqlite --sqlite PATH --dry-run\|--apply [--report FILE] [--email-domain D]` | backup SQLite (online API) + `pg_dump` target; transform; one transaction; verify; rollback on dry-run; JSON report |
| `admin create EMAIL --role admin\|superadmin` | prompts password twice (bootstrap of the first superadmin) |
| `user reset-password EMAIL` / `user set-active EMAIL --on\|--off` / `user set-role EMAIL USER\|ADMIN\|SUPERADMIN` | same services and guards as the API |
| `system-dict list \| seed \| import FILE [--mode ...] \| export DIR \| enable NAME \| disable NAME` | `seed` loads bundled packs only when none exist |
| `voices sync` / `voices render-samples [--only ID]` | phase 3 sync; render a fixed sentence per voice via engine into `voices/samples/<id>.mp3` |

Mapping: users -> users (new UUID; trial defaults; terms not accepted); api_keys -> developer_api_keys (LIVE, prefix, hash, last_used_at, revoked_at); dictionaries/entries -> system_dictionaries/system_pronunciation_rules (whole_word true, sort_order = entry id order, `rule_kind` per rule above, note kept); sessions and meta not migrated (counted).

Verification (both modes): per-table counts; set equality of password hashes, key hashes and reverse-mapped `(term, replacement, mode, case_sensitive, note)` tuples; VARCHAR overflow is a hard error with row ids; exit 0 only with `lost_rows: 0`.

## Related code files
Create: `src/vieneu_portal/admin_services/user_account_admin_service.py`, `admin_services/role_change_guards.py`, `admin_services/admin_audit_log_writer.py`, `dictionaries/system_dictionary_store.py`, `admin_cli/cli_parser_and_dispatch.py`, `admin_cli/commands_users_and_admins.py`, `admin_cli/commands_system_dictionaries.py`, `admin_cli/commands_voices.py`, `sqlite_migration/sqlite_admin_reader.py`, `sqlite_migration/legacy_rows_to_portal_rows.py`, `sqlite_migration/migration_verification_report.py`, `sqlite_migration/run_sqlite_to_postgres_migration.py`, `src/vieneu_portal/seed/system_dictionaries/*.json` (move from `src/vieneu_admin/seed/`), tests `tests/portal/test_sqlite_to_postgres_migration.py`, `test_portal_admin_cli.py` (not `test_admin_cli.py`: duplicate test basenames across `tests/` collide under pytest's default import mode), `test_role_change_guards.py`, `test_system_dictionary_store.py`, `tests/fixtures/legacy_admin_sqlite_builder.py`.
Modify: `src/vieneu_portal/__main__.py` (dispatch), `tests/test_seed_dictionaries.py` (`SEED_DIR`, `:9`), `pyproject.toml` package-data (seed path).

## Implementation steps
1. Move seed packs; fix seed test path.
2. Audit writer, guards, user admin service (+ tests: last superadmin, concurrent double demotion, self-demotion).
3. System dictionary store with `rule_kind` mapping both ways; JSON/txt import, export, `seed`.
4. Read-only SQLite reader after online backup; pure transforms + verification on a fixture with edge rows (non-email username, disabled user, revoked key, `en` with and without replacement, case-sensitive duplicates, unicode).
5. Transactional runner with `pg_dump` pre-step, dry-run rollback, idempotent apply.
6. CLI commands driving the services; tests via `main(argv)` against real Postgres.
7. Dry-run on a copy of the real `vieneu_data/admin.sqlite3` if present; note the report path.

## Todo
- [ ] seed move  - [ ] audit + guards + user services  - [ ] system dict store  - [ ] reader/transform/verify  - [ ] runner  - [ ] CLI  - [ ] tests  - [ ] real-copy dry run

## Success criteria
- Fixture dry-run `lost_rows: 0`, DB unchanged; apply twice -> second inserts 0 rows; migrated user logs in with the old password.
- Every CLI mutation leaves one audit row; guard tests green.

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| Synthetic emails | M x M | Report lists them; admin edits email in phase 14 UI |
| Old regex-boundary matching vs new whole-word | M x M | Phase 7 vectors cover symbol-edged terms (`C++`, `.NET`) |
| Partial apply | L x H | Single transaction; verification failure rolls back |

## Rollback
Restore the pre-apply `pg_dump`; SQLite source is never written.

## Security
Report has counts and usernames only; passwords via `getpass`; audit rows never contain password hashes.

## Next
Phase 6 deletes `vieneu_admin`; phase 13 exposes the services over HTTP.
