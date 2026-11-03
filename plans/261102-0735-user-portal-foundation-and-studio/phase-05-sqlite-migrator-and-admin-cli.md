# Phase 05: SQLite -> Postgres migrator, system dictionary layer, admin services and CLI

<!-- Updated: Red Team 2026-11-02 - seed packs copied (old admin still runs until phase 6); provenance ids + abort-on-conflict; privileged-account creation guard; voices sync from engine; text preview CLI replaces Script Lab; system layer cache + cap -->

## Context
- Source schema: `src/vieneu_admin/db.py:27-70` (users int id/username/scrypt hash/role admin|user/active; api_keys prefix+sha256; sessions; dictionaries kind english/term/name; dictionary_entries term/replacement/mode phonetic|en/case_sensitive/note with `UNIQUE (dictionary_id, term_key)` `:67`; meta).
- Legacy usernames match `^[A-Za-z0-9_.-]{3,40}$` (`src/vieneu_admin/store_accounts.py:14`), so none is an email.
- The legacy engine auto-seeds the same 7 packs under the same names on start (`apps/openai_speech.py:325`, `src/vieneu_admin/store.py:79-99`), so real SQLite files already hold packs with the bundled names, possibly with admin edits.
- SQLite online backup pattern: `src/vieneu_admin/db.py:144-159`. Old CLI to replace: `src/vieneu_admin/cli.py:28-88`.
- Dictionary JSON format `vieneu-dictionary/1`: `src/vieneu_preprocess/dictionary_schema.py:60-129`; `mode=en` ignores `replacement` (`src/vieneu_preprocess/types.py:12-17`).
- Seed packs: `src/vieneu_admin/seed/*.json` (7 files, 848 entries: term/phonetic 316, english/en 273, name/phonetic 130, term/en 125, name/en 4).
- Engine understands `<en>...</en>` (`src/vieneu_utils/core_utils.py:14-21`).

## Overview
Priority P1. Lossless one-time import of users, API keys and global dictionaries with provenance; seed packs become the system dictionary layer; admin service functions (shared by this CLI and the phase 13 API, DRY) with audit logging; minimal CLI for headless setups, including a text preview that replaces Script Lab. Backups precede every write.

## Key insights
- SQLite users have no email: every migrated user gets `<username>@<MIGRATION_EMAIL_DOMAIN>` (default `migrated.invalid`, reserved at signup by phase 2), listed in the report as `needs_email`; admins fix it in the admin UI. Login works with that address (phase 2 uses a plain lookup).
- Old role `admin` -> `SUPERADMIN` (it had full power), `user` -> `USER`. Hashes copy verbatim (same formats as phase 2).
- `<en>` entries (user decision, interpretation confirmed in Validation Session 1): `mode=en` with non-empty replacement -> normal `REPLACE` rule; `mode=en` with empty replacement -> `ENGLISH_FALLBACK` rule (matched text wrapped in `<en>...</en>`, lowest tie priority). All 402 seed `en` entries have empty replacement, so they become the fallback list. Export maps back (`ENGLISH_FALLBACK` -> `mode: "en"`), so JSON round-trips.
- Idempotency by provenance, not natural keys alone: users and packs carry `legacy_source_id` (`sqlite:users:<id>`, `sqlite:dictionaries:<id>`); keys by `key_hash`; rules by `(dictionary_id, term_key)`. A natural-key match (`lower(email)`, pack `name`) on a row without the same `legacy_source_id` is a conflict: apply aborts and the report lists every conflict. No silent skip, no silent upsert of role or hash.
- Order (runbook, enforced): `migrate-sqlite --apply` before `system-dict seed` and before opening signup; `system-dict seed` refuses when any pack exists; `migrate-sqlite --apply` refuses when the target has users or packs without `legacy_source_id`, unless `--allow-existing` is passed (conflicts still abort).
- The old admin keeps reading `src/vieneu_admin/seed/` until phase 6, so the seed packs are copied here and the admin copy is deleted in phase 6.

## Requirements
Admin services (`src/vieneu_portal/admin_services/`), each mutation writes one `admin_audit_log` row in the same transaction:
- `create_user_by_admin(actor, email, username, password, role)`: role `ADMIN`/`SUPERADMIN` only when the actor is SUPERADMIN (CLI actor counts as SUPERADMIN), else `403 FORBIDDEN_ROLE`; `reset_password` (revokes sessions), `set_user_active` (revokes sessions on disable), `set_user_role` with guards: cannot remove/disable/delete the last active SUPERADMIN (`409 LAST_SUPERADMIN`), cannot change own role or disable/delete self (`409 SELF_MODIFICATION`). Guard query locks SUPERADMIN rows (`FOR UPDATE`) to avoid two concurrent demotions both passing.
- System dictionary store: pack CRUD, rule list/replace-all, JSON import (`new|merge|replace`) and export, `.txt/.csv` import into a pack via the phase 7 parser; total enabled system rules capped at `SYSTEM_RULES_MAX` (`422 SYSTEM_RULES_LIMIT_EXCEEDED`). Every mutation bumps the pack `updated_at`, which keys the compiled system-layer cache (phase 9).
- Rule targets are moderated on save/import (phase 8 provider; rejected rows reported with line/index).
- `write_admin_audit(actor, action, target, before, after, ip)`; CLI actor label `cli:<os-user>`.

CLI `python -m vieneu_portal <group> <command>`:
| Command | Behavior |
|---|---|
| `migrate-sqlite --sqlite PATH --dry-run\|--apply [--report FILE] [--allow-existing]` | backup SQLite (online API) + `pg_dump` target; transform; one transaction; verify; rollback on dry-run; JSON report incl. `conflicts` |
| `admin create EMAIL --role admin\|superadmin` | prompts password twice (bootstrap of the first superadmin) |
| `user reset-password EMAIL` / `user set-active EMAIL --on\|--off` / `user set-role EMAIL USER\|ADMIN\|SUPERADMIN` | same services and guards as the API |
| `system-dict list \| seed \| import FILE [--mode ...] \| export DIR \| enable NAME \| disable NAME` | `seed` loads bundled packs only when no pack exists |
| `voices sync` / `voices render-samples [--only ID]` | phase 3 sync from the engine's `/v1/voices`; render a fixed sentence per voice via engine into `voices/samples/<id>.mp3` |
| `text preview TEXT [--user EMAIL] [--voice ID]` | runs `build_engine_text` with the DB rules (system layer, plus the user's account rules when given) and prints processed text, char count and tokens; replaces Script Lab with output identical to what the portal sends to the engine |

Mapping: users -> users (new UUID; `legacy_source_id`; trial defaults; terms not accepted); api_keys -> developer_api_keys (LIVE, prefix, hash, last_used_at, revoked_at; stored for the C2 developer API, not usable by the engine after phase 6); dictionaries/entries -> system_dictionaries/system_pronunciation_rules (`legacy_source_id` on packs, whole_word true, sort_order = entry id order, `rule_kind` per rule above, note kept); sessions and meta not migrated (counted; the CSRF secret is replaced by `SECRET_KEY`).

Verification (both modes): per-table counts; set equality of password hashes, key hashes and reverse-mapped `(term, replacement, mode, case_sensitive, note)` tuples; VARCHAR overflow is a hard error with row ids; exit 0 only with `lost_rows: 0` and `conflicts: []`.

## Related code files
Create: `src/vieneu_portal/admin_services/user_account_admin_service.py`, `admin_services/role_change_guards.py`, `admin_services/admin_audit_log_writer.py`, `dictionaries/system_dictionary_store.py`, `admin_cli/cli_parser_and_dispatch.py`, `admin_cli/commands_users_and_admins.py`, `admin_cli/commands_system_dictionaries.py`, `admin_cli/commands_voices.py`, `admin_cli/commands_text_preview.py`, `sqlite_migration/sqlite_admin_reader.py`, `sqlite_migration/legacy_rows_to_portal_rows.py`, `sqlite_migration/migration_verification_report.py`, `sqlite_migration/run_sqlite_to_postgres_migration.py`, `src/vieneu_portal/seed/system_dictionaries/*.json` (copied from `src/vieneu_admin/seed/`), tests `tests/portal/test_sqlite_to_postgres_migration.py`, `test_portal_admin_cli.py` (not `test_admin_cli.py`: duplicate test basenames across `tests/` collide under pytest's default import mode), `test_role_change_guards.py`, `test_system_dictionary_store.py`, `tests/fixtures/legacy_admin_sqlite_builder.py`.
Modify: `src/vieneu_portal/__main__.py` (dispatch), `tests/test_seed_dictionaries.py` (`SEED_DIR` `:9` -> portal copy), `pyproject.toml` package-data (portal seed path).

## Implementation steps
1. Copy seed packs; point the seed test at the portal copy.
2. Audit writer, guards, user admin service (+ tests: last superadmin, concurrent double demotion, self-demotion, ADMIN actor creating ADMIN/SUPERADMIN -> 403).
3. System dictionary store with `rule_kind` mapping both ways; JSON/txt import, export, `seed`, system rule cap, target moderation.
4. Read-only SQLite reader after online backup; pure transforms + verification on a fixture with edge rows (disabled user, revoked key, `en` with and without replacement, case-sensitive duplicates, unicode, a pack edited away from its seed values).
5. Transactional runner with `pg_dump` pre-step, dry-run rollback, idempotent apply by provenance, conflict detection (pre-existing signup with a migrated email, pre-seeded pack with a legacy name) -> abort with named list.
6. CLI commands driving the services, including `text preview`; tests via `main(argv)` against real Postgres and the engine double.
7. Dry-run on a copy of the real `vieneu_data/admin.sqlite3` if present; note the report path.

## Todo
- [ ] seed copy  - [ ] audit + guards + user services  - [ ] system dict store  - [ ] reader/transform/verify  - [ ] runner + conflicts  - [ ] CLI incl. text preview  - [ ] tests  - [ ] real-copy dry run

## Success criteria
- Fixture dry-run `lost_rows: 0`, `conflicts: []`, DB unchanged; apply twice -> second inserts 0 rows; migrated user logs in over HTTP with the old password and the `@migrated.invalid` address.
- Apply against a DB with a squatting signup or a pre-seeded pack aborts and names the conflict.
- Every CLI mutation leaves one audit row; guard tests green.

## Risk
| Risk | L x I | Mitigation |
|---|---|---|
| Synthetic emails | M x M | Report lists them; admin edits email in phase 14 UI |
| Old regex-boundary matching vs new whole-word | M x M | Phase 7 vectors cover symbol-edged terms (`C++`, `.NET`); `text preview` shows the new result |
| Partial apply | L x H | Single transaction; verification failure rolls back |
| Signup squats a migrated email before apply | L x H | Reserved migration domain at signup; provenance conflict aborts apply; runbook: migrate before enabling signup (`SIGNUP_ENABLED=false` until done) |

## Rollback
Restore the pre-apply `pg_dump`; SQLite source is never written.

## Security
Report has counts and usernames only; passwords via `getpass`; audit rows never contain password hashes.

## Next
Phase 9 (account dictionaries use the system store), phase 13 exposes the services over HTTP, phase 6 deletes `vieneu_admin` at the end.
