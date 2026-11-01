# Verification: admin web app, dictionaries and story preprocessor

- Plan: `plans/261030-0731-admin-web-dictionary-preprocessor/`
- Branch: `main-bkt` (working tree, uncommitted)
- Date: 2026-11-01 07:23 (Asia/Saigon)
- Environment: Windows 11, repo `.venv` (Python 3.12). No model weights loaded; engine replaced by the test-suite `FakeTTS` where audio is involved.

## Summary

Seven of eight plan success criteria are verified here, through the test suite plus a walkthrough against the real FastAPI app (web forms, API, Help page) on a temporary database. The real-model `[0.5]` silence check is left open because it needs the model. Docker image builds, `uv lock` and listening to the seed pronunciations were not run either; the commands for the ear check are in section 4.

## 1. Commands run

| Check | Command | Result |
|---|---|---|
| Full test suite | `.venv\Scripts\python.exe -m pytest tests -q` | **426 passed, 4 skipped**, 48.7 s, exit 0 (4 FastAPI `on_event` deprecation warnings) |
| Acceptance walkthrough (scratch, not committed) | `pytest <scratchpad>/verify/test_acceptance_walkthrough.py` with `PYTHONPATH=.;src;tests` | **6 passed**: full admin/user/key/revoke flow, roles + CSRF, DB hash-only dump, env key + `VIENEU_ADMIN=0`, Help for 4 docs × EN/VI |
| Seed + spec §5.1 check (scratch) | `seed_check.py`: fresh `AdminStore`, `seed_if_empty()`, `preprocess(dracaena_input.md, enabled_lexicon())` | 7 dictionaries seeded, all enabled, 848 merged entries; `Hốc-goát`, `Sờ-li-thơ-rin`, `Đờ-ra-xê-na` present; countdown `[0.6, 0.85, 1.1, 1.4]` |
| Compose config | `docker compose -f docker/docker-compose.yml --profile api-gpu --profile api-cpu config --quiet` | OK; `VIENEU_ADMIN=1`, `vieneu_data:/workspace/vieneu_data`, `FORWARDED_ALLOW_IPS=127.0.0.1` resolved |
| Compose config (prod) | `docker compose -f docker/docker-compose.prod.yml --profile api config --quiet` | Fails only because `docker/.env` is absent here (`env_file` is required in the prod file; this predates the plan) |

Not run: `uv run pytest` (instruction: use the venv interpreter), `uv lock`, Docker image builds, real-model rendering, manual browser session, listening to audio.

## 2. Success criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Fresh DB + env creds: admin logs in, creates user; user logs in, creates key; API call with key gets audio; revoked → 401. `VIENEU_API_KEY` works. Admin on + no keys → 401; `VIENEU_ADMIN=0` → old behavior | **Pass** (fake engine) | Walkthrough `test_criterion_1_and_2_full_flow`: `/` → 303 `/admin/`; speech without key 401; root logs in via form, `POST /admin/users` creates bob; bob logs in, `POST /admin/keys` shows `vn_…` once (absent from later list); speech with key 200 + `RIFF`; bob revokes via form; same call 401. `test_env_key_and_admin_off`: env key 200 with admin on; `VIENEU_ADMIN=0` keyless 200 and `/admin/login` 404. Suite: `test_admin_on_with_zero_keys_rejects_every_call`, `test_db_key_accepted_then_revoked`, `test_disabled_user_key_rejected`, `test_env_key_still_accepted_with_admin_on`, `test_admin_off_without_env_key_stays_open`, `test_fresh_db_without_admin_credentials_refuses_to_start` |
| 2 | DB holds only hashes; non-admin 403 on `/admin/users*` and dictionary writes; POST without CSRF 403 | **Pass** | Walkthrough: `sqlite3 iterdump` of the DB contains neither the key, the two passwords, nor bob's session cookie; bob gets 403 on `GET/POST /admin/users`, `POST /admin/dictionaries`, `POST /admin/dictionaries/1/toggle`; POST without token 403 for both user and admin. Schema check: `users.password_hash`, `api_keys.key_hash`, `sessions.token_hash` only. Suite: `test_session_expiry_and_hash_only_storage`, `test_non_admin_gets_403_on_admin_routes`, `test_csrf_required` |
| 3 | Export → import into empty DB round-trips exactly; malformed JSON shows line and column | **Pass** | Suite: `test_import_new_export_round_trip_into_empty_db`, `test_export_and_import_round_trip` (CLI), `test_round_trip_sorted_utf8`, `test_broken_json_has_line_column`, `test_import_merge_replace_and_errors` |
| 4 | Seeds exist after first start; §5.1 input yields `Hốc-goát`, `Sờ-li-thơ-rin`, `Đờ-ra-xê-na` | **Pass** | `seed_check.py` with the real seed files and default rules (all three present). Suite: `test_startup_bootstraps_admin_seeds_and_never_logs_the_password`, `test_seed_if_empty`, `test_key_phonetic_entries` |
| 5 | Unit tests prove §5.2/§5.3 structure: speaker turns, inner-voice split, countdown `0.6 → 0.85 → 1.1 → 1.4`, shout normalization, drop-cap recovery, embedded-quote guard | **Pass** | `test_speaker_turns_match_spec_5_2`, `test_inner_voice_split`, `test_countdown_pauses`, `test_shout_normalization`, `test_drop_cap_and_lexicon_names`, `test_drop_cap_recovery`, `test_embedded_quote_guard_keeps_narration`, `test_json_shape_matches_spec_5_3` |
| 6 | `[0.5]` in API input yields about 0.5 s of silence and is never spoken; untagged input gives the same chunks and gaps as before | **Partial: logic verified, real-model check not run** | Fake-engine/chunker tests: `test_untagged_text_matches_snapshot`, `test_tag_never_reaches_chunk_text_or_phonemes`, `test_infer_inserts_exact_internal_pauses`, `test_infer_leading_and_trailing_pauses`, `test_infer_stream_pauses`, `test_infer_solo_pause_tag_is_pure_silence`. A listening/waveform check with the real model needs the user (section 4, command C) |
| 7 | `/admin/help` renders all four docs with an EN/VI switch; `docs/` is the only copy | **Pass** | Walkthrough `test_help_renders_real_docs[guide|functions × en|vi]`: 200, no missing-doc banner, tables + code blocks + headings rendered (functions: 13 tables, 4 code blocks; guide: 1 table, 6 code blocks), escaped `\|` stays inside one table cell. Only copy: the four files exist once, under `docs/` (Docker copies `docs/` into the image at build time). Path-traversal guard: `test_help_rejects_unknown_doc_or_lang` |
| 8 | `uv run pytest` passes in full | **Pass (equivalent)** | Ran with `.venv\Scripts\python.exe -m pytest tests -q` as instructed, not via `uv run`: 426 passed, 4 skipped |

## 3. Phase checklist status

| Phase | Boxes | Status set | Note |
|---|---|---|---|
| 1 | 3/4 | completed | `uv lock` not run, so the first box stays open. `pyproject.toml` and `.gitignore` edits are in place (`jinja2`, `markdown-it-py`, `vieneu-preprocess` script, package data; `vieneu_data/` ignored). |
| 2–6 | all | completed | Each box maps to code plus passing tests (see criteria above). |
| 7 | all | completed | This report and the four docs. |

Deviation noted in phase 6: static files are served by a whitelisted router route (`GET /admin/static/{name}`, three files) rather than `app.mount("/admin/static", StaticFiles(...))`. Same URLs, stricter; boxes ticked.

## 4. Ear check for the user

### Seed dictionary files (`src/vieneu_admin/seed/`)

| File | Name | Kind | Entries |
|---|---|---|---|
| `abbreviations.json` | Từ viết tắt | term | 161 |
| `business-finance.json` | Kinh doanh và tài chính | term | 79 |
| `english-common.json` | Tiếng Anh thông dụng | english | 273 |
| `fantasy-ash-land.json` | Kỳ huyễn: Vùng Đất Tro Tàn | name | 60 |
| `fantasy-hogwarts.json` | Kỳ huyễn: Hogwarts | name | 74 |
| `it-terms.json` | Thuật ngữ công nghệ | term | 125 |
| `medical.json` | Y tế | term | 76 |

### Sample commands

A. CLI, spec §5.1 sample with the seeds and the cast hints, one WAV (uses the local model):

```bash
uv run vieneu-preprocess tests/fixtures/preprocess/dracaena_input.md \
  --dict src/vieneu_admin/seed/*.json \
  --rules tests/fixtures/preprocess/dracaena_cast_rules.yaml \
  --render --voice "Mai Anh" --out out/ear-check
# -> out/ear-check/dracaena_input.script.txt, .json, .wav
uv run vieneu-preprocess tests/fixtures/preprocess/ash_land_sample.md \
  --dict src/vieneu_admin/seed/*.json --render --voice "Mai Anh" --out out/ear-check
```

B. Server, Script Lab, API (both fixtures are under the 3 000-character render limit, so they can also be pasted into Script Lab):

```bash
VIENEU_ADMIN_USER=admin VIENEU_ADMIN_PASSWORD='change-me-please' uv run python -m apps.openai_speech
# log in at http://127.0.0.1:8000/admin, create a key, then:
uv run python - <<'EOF'
import pathlib
from openai import OpenAI
c = OpenAI(base_url="http://127.0.0.1:8000/v1", api_key="vn_PASTE_KEY")
text = pathlib.Path("tests/fixtures/preprocess/dracaena_input.md").read_text(encoding="utf-8")
with c.audio.speech.with_streaming_response.create(model="vieneu-v3-turbo", voice="Mai Anh",
        input=text, response_format="wav", extra_body={"preprocess": True}) as r:
    print(r.headers.get("X-VieNeu-Preprocess"), r.headers.get("X-VieNeu-Ignored"))
    r.stream_to_file("dracaena-api.wav")
EOF
```

C. Pause tags with the real model (criterion 6):

```bash
curl -s http://127.0.0.1:8000/v1/audio/speech -H "Authorization: Bearer vn_PASTE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": "[0.5] Xin chào. [1.5] Tạm biệt. [0.5]", "response_format": "wav"}' -o pauses.wav
```

Expect exactly 0.5 s silence at both ends, at least 1.5 s between the two sentences, and no tag spoken.

Listen for: Hogwarts names (`Hốc-goát`, `Sờ-li-thơ-rin`, `Đờ-ra-xê-na`, `Gờ-ríp-phin-đo`, `Mắc-go-na-gôn`), Ash Land names, a few abbreviations (`VTV`, `GDP`), IT and medical terms in sentences, and English-mode words (`Scotland`). Fix wrong spellings in the app (User guide §5 "Fix a seed pronunciation") and export the corrected dictionary.

## 5. Docs delivered

| File | Lines |
|---|---|
| `docs/web-admin-functions.md` / `.vi.md` | 317 / 317 |
| `docs/user-guide.md` / `.vi.md` | 199 / 199 |
| `README.md`, `README.vi.md` | new "Admin web app" / "Trang quản trị web" section under §3 |

Vietnamese files mirror the English heading structure and table rows exactly (scripted heading/table comparison). Every route, env var, default and limit in the docs was read from source: `apps/openai_speech.py`, `src/vieneu_admin/*`, `src/vieneu_preprocess/*`, `src/vieneu_utils/core_utils.py`, `docker/*`, `.env.example`.

Required notes are all covered: breaking change (key required, `VIENEU_ADMIN=0`, fresh-DB refusal, Docker `vieneu_data`), `FORWARDED_ALLOW_IPS`, Script Lab limits (50 000 / 3 000, WAV/FLAC), pause-tag range and clamping (0–5 s, adjacent tags sum, leading/trailing exact, inter-chunk minimum), speed by resampling shifts pitch, Hogwarts cast hints not in the default rules, and export visible to every logged-in user.

## 6. Findings (reported, not fixed)

1. **In-app relative link.** `docs/web-admin-functions*.md` links `../src/vieneu_preprocess/config/pause_rules.yaml` (required by the phase: "link, do not copy numbers"). On GitHub it resolves; inside `/admin/help` it points to `/src/...` and 404s. The link text shows the path, so readers can still find the file. Low impact.
2. **Seeds return after deleting all dictionaries.** `seed_if_empty` imports the seeds whenever the database has zero dictionaries, so an admin who deletes every dictionary gets the seeds back on the next restart. Documented; may or may not be intended.
3. **Prod compose needs `docker/.env`.** `docker-compose.prod.yml` declares `env_file` as required, so `config`/`up` fails without that file. It predates this plan; noted for operators.
4. **Venv editable install is stale.** Importing `apps.openai_speech` outside pytest failed with `No module named 'vieneu_preprocess'` until `src` was put on `PYTHONPATH`; pytest works through `pythonpath = ["src"]`. A `uv sync` or reinstall refreshes the editable install so `python -m apps.openai_speech` and `vieneu-preprocess` work in this venv.
5. **Lockout resets on restart.** It is in memory by design; documented.

## Unresolved questions

1. Plan-level front matter `status:` in `plan.md` is still `pending`. Should it become `completed` now, or wait for the ear check and the real-model `[0.5]` check?
2. Should deleting every dictionary really re-seed on restart (finding 2), or should seeding happen only on a brand-new database?
3. Is it acceptable that every logged-in user can export dictionaries, or should export be admin-only?
