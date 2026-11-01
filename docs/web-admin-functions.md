# Web admin functions

Reference for operators and maintainers of the VieNeu admin web app, the pronunciation dictionaries and the story preprocessor. For step-by-step tasks, read the **User guide** (Help → User guide, file `docs/user-guide.md`). Vietnamese version: `docs/web-admin-functions.vi.md`.

> **Breaking change for keyless API setups.** When the admin app is on (the default, `VIENEU_ADMIN=1`), **every** `/v1/*` call needs an API key, even before any key exists: the first calls after an upgrade get `401` until you create a key at `/admin/keys` or set `VIENEU_API_KEY`. `VIENEU_ADMIN=0` restores the old behavior exactly (open API unless `VIENEU_API_KEY` is set).
>
> On a **fresh database** with no admin account, the server **refuses to start** unless `VIENEU_ADMIN_USER` and `VIENEU_ADMIN_PASSWORD` are set (or `python -m vieneu_admin create-admin <user>` ran first). This affects Docker: the `api-gpu`, `api-cpu` and prod `api` services keep the database in the persistent `vieneu_data` volume, so the first start on a new volume needs those two variables. Behind a reverse proxy, set `FORWARDED_ALLOW_IPS` to the proxy address, or the login lockout sees every client as the proxy.

## 1. Architecture

One process (`apps/openai_speech.py`, one uvicorn worker) serves both the OpenAI-compatible speech API and the admin app. The admin package `src/vieneu_admin/` never imports the engine; the API hands it an engine provider for Script Lab.

```text
 API client ──Bearer key──▶ /v1/audio/speech ──▶ key check ─┐
                                 │                           │
                                 │ preprocess=true           ▼
                                 ▼                     SQLite (vieneu_data/admin.sqlite3)
                     vieneu_preprocess.preprocess ◀── enabled dictionaries (lexicon)
                                 │ text with [x.xx] tags       ▲
                                 ▼                             │
                     VieNeuV3Turbo.infer_stream          users, keys, sessions,
                                                         dictionaries
 Browser ──session cookie──▶ /admin (Jinja2 + HTMX) ──────────┘
                                 │ Script Lab render
                                 ▼
                     vieneu_preprocess.render (per-chunk voice, speed, pauses)
                                 │ one stream slot, through infer_stream
                                 ▼
                              engine
 /admin/help ──▶ docs/web-admin-functions[.vi].md, docs/user-guide[.vi].md
```

Startup order: open the database, run migrations, load seed dictionaries if the database has none, make sure an active admin exists (or abort), mount `/admin`, then load the model. A configuration error therefore stops the server before the model spends time loading.

## 2. Pages and routes

All admin routes live under `/admin`. "User" means any logged-in active account; "Admin" means the `admin` role. Every `POST` needs a valid CSRF token (form field `csrf_token` or header `X-CSRF-Token`), otherwise `403`. Without a session, pages redirect to `/admin/login` (`303`); HTMX requests get `401` with an `HX-Redirect` header. A non-admin on an admin-only route gets `403`.

### Account

| Method and path | Who | What it does |
|---|---|---|
| `GET /admin/login` | anyone | Login form (redirects to the dashboard when already logged in). |
| `POST /admin/login` | anyone | Checks the credentials; 5 failures per (username, client IP) within 5 minutes lock that pair for the rest of the window (`429`). |
| `POST /admin/logout` | User | Ends the session. |
| `GET /admin/` | User | Dashboard: your active key count, enabled dictionaries, engine status. |
| `GET /admin/account/password` | User | Change-password form. |
| `POST /admin/account/password` | User | Needs the current password; signs out every other session of the account. |

### API keys

| Method and path | Who | What it does |
|---|---|---|
| `GET /admin/keys` | User | Your keys. Admins see every key, with its owner. |
| `POST /admin/keys` | User | Creates a key named 1–80 characters. The full key (`vn_…`) is shown **once**, on this response only. |
| `POST /admin/keys/{id}/revoke` | User | Revokes your own key; admins may revoke any key. Another user's key gives `403`. |

### Users (admin only)

| Method and path | What it does |
|---|---|
| `GET /admin/users` | List of accounts. |
| `POST /admin/users` | Create an account (role `user` or `admin`). |
| `POST /admin/users/{id}/role` | Change the role. |
| `POST /admin/users/{id}/active` | Enable or disable; disabling ends the user's sessions and their keys stop working. |
| `POST /admin/users/{id}/password` | Reset the password; ends the user's sessions. |
| `POST /admin/users/{id}/delete` | Delete the account and its keys. |

Guards: the last active admin can never be demoted, disabled or deleted; an admin cannot demote, disable, reset the password of, or delete their own account from this page (use **Change password** for your own password). Usernames are 3–40 characters of letters, digits, `.`, `_` or `-`; passwords are 8–256 characters.

### Dictionaries

| Method and path | Who | What it does |
|---|---|---|
| `GET /admin/dictionaries` | User | List with kind, status and entry count. |
| `POST /admin/dictionaries` | Admin | Create an empty dictionary. |
| `POST /admin/dictionaries/import` | Admin | Upload JSON (max 5 MB): `new`, `merge` into, or `replace` the entries of an existing dictionary. |
| `POST /admin/dictionaries/preview` | User | Preprocess one sentence (max 2 000 characters) with one dictionary or with every enabled one, and show the tagged result. |
| `GET /admin/dictionaries/{id}` | User | Entries, 50 per page, with search. |
| `GET /admin/dictionaries/{id}/export` | User | Download the dictionary as `vieneu-dictionary/1` JSON. |
| `POST /admin/dictionaries/{id}/rename` | Admin | Rename and edit the description. |
| `POST /admin/dictionaries/{id}/toggle` | Admin | Enable or disable. |
| `POST /admin/dictionaries/{id}/delete` | Admin | Delete with all entries. |
| `POST /admin/dictionaries/{id}/entries` | Admin | Add an entry. |
| `GET /admin/dictionaries/{id}/entries/{entry_id}` | User | One entry row (used by inline editing). |
| `GET /admin/dictionaries/{id}/entries/{entry_id}/edit` | Admin | Inline edit form. |
| `POST /admin/dictionaries/{id}/entries/{entry_id}` | Admin | Save an entry. |
| `POST /admin/dictionaries/{id}/entries/{entry_id}/delete` | Admin | Delete an entry. |

> **Export visibility.** Every logged-in user, not only admins, can view dictionary entries and download the JSON export. Do not store anything confidential in a dictionary.

### Script Lab

| Method and path | Who | What it does |
|---|---|---|
| `GET /admin/script-lab` | User | Page with the text box and limits. |
| `POST /admin/script-lab/preprocess` | User | Analyse up to **50 000 characters**: formatted script, speakers, chunk JSON. |
| `GET /admin/script-lab/download.json` | User | Chunk JSON of your last analysis. |
| `POST /admin/script-lab/render` | User | Render audio for up to **3 000 characters**, format **WAV** (default) or **FLAC**, with a voice per speaker. One render at a time per session (`429` otherwise); `503` "Engine not loaded" without a model. |
| `GET /admin/script-lab/audio` | User | Play (`inline`) or download (`?download=1`) your last render. |

The last analysis and render are kept in process memory per session only (across all users, the 64 most recent analyses and the 8 most recent renders); a restart drops them, so download what you want to keep. Longer texts are rendered with the `vieneu-preprocess` CLI (section 8).

### Help and other

| Method and path | Who | What it does |
|---|---|---|
| `GET /admin/help?doc=guide\|functions&lang=en\|vi` | User | Renders this document or the user guide. Only those four files can be opened. |
| `GET /admin/static/{name}` | anyone | Only `htmx.min.js`, `app.js`, `app.css`. |
| `GET /` | anyone | Redirects to `/admin/` when the admin app is on (`404` otherwise). |

## 3. Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `VIENEU_ADMIN` | `1` | `0` turns the admin app off and restores the keyless API (only the value `0` disables it). |
| `VIENEU_ADMIN_DB` | `vieneu_data/admin.sqlite3` (relative to the working directory; Docker `/workspace/vieneu_data/admin.sqlite3`) | SQLite database path. Git-ignored. |
| `VIENEU_ADMIN_USER`, `VIENEU_ADMIN_PASSWORD` | unset | First admin on a database with no active admin. Required on a fresh database. Ignored once an active admin exists, so they never overwrite a password changed in the app. The password is never logged. |
| `VIENEU_API_KEY` | unset | Extra shared key, always accepted as `Bearer <key>`. With `VIENEU_ADMIN=0` and this unset, the API is open. |
| `VIENEU_COOKIE_SECURE` | `0` | `1` marks the session and CSRF cookies `Secure` (set it when `/admin` is served over HTTPS; requests that arrive as `https` get it automatically). |
| `VIENEU_DOCS_DIR` | repository `docs/` (Docker `/workspace/docs`) | Folder the Help page reads. |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | Proxies whose `X-Forwarded-For` is trusted, so the login lockout sees the real client IP. |
| `HOST`, `PORT` | `127.0.0.1`, `8000` | Listening address. Docker sets `HOST=0.0.0.0`. |

The engine variables (`VIENEU_BACKEND`, `VIENEU_MAX_STREAMS`, `VIENEU_QUEUE`, `VIENEU_QUEUE_TIMEOUT`, …) are unchanged; see `docs/streaming.md`.

At startup the log states the mode: `admin app at /admin … every /v1/* call requires an API key (N active)`, plus a warning when no key exists yet, or `admin app off (VIENEU_ADMIN=0)` with whether `/v1/*` is open.

## 4. Database

- SQLite file at `VIENEU_ADMIN_DB` with tables `users`, `api_keys`, `sessions`, `dictionaries`, `dictionary_entries`, `meta`, `schema_version`.
- **Only hashes are stored:** passwords as scrypt (`scrypt$N$r$p$salt$hash`), API keys and session tokens as SHA-256. A key's first 8 characters (`vn_…`) are kept as a display prefix.
- Sessions last 12 hours and slide forward while in use.
- **Backups before migrations:** before a schema migration runs on an existing file, the server checkpoints the WAL and writes a consistent copy with SQLite's online-backup API next to the database: `admin.sqlite3.bak-v<old version>-<timestamp>`.
- **Your own backups:** the database runs in WAL mode, so do not copy the `.sqlite3` file alone while the server runs. Use `sqlite3 vieneu_data/admin.sqlite3 ".backup backup.sqlite3"`, or stop the server first. To keep dictionaries portable, also export them (`python -m vieneu_admin export-dicts DIR`).
- **Seeding:** on startup, when the database has **no dictionaries at all**, every file in `src/vieneu_admin/seed/*.json` is imported. Deleting every dictionary therefore brings the seeds back on the next start.
- Docker keeps the file in the `vieneu_data` volume (`/workspace/vieneu_data`). Removing the volume deletes users, keys and dictionaries.

## 5. Speech API changes

### Authentication

| Mode | Accepted `Authorization` | No key or wrong key |
|---|---|---|
| Admin app on (`VIENEU_ADMIN=1`, default) | `Bearer vn_…` (active key of an active user) or `Bearer $VIENEU_API_KEY` | `401`, even when no key exists yet |
| Admin app off (`VIENEU_ADMIN=0`), `VIENEU_API_KEY` set | `Bearer $VIENEU_API_KEY`, and database keys if the database file exists | `401` |
| Admin app off, `VIENEU_API_KEY` unset | anything (open, as before) | — |

A revoked key, or a key of a disabled user, is rejected at once. `GET /health` never needs a key. If the key lookup itself fails (database error), the API answers `503` with `Retry-After: 5`.

### `preprocess` field

`POST /v1/audio/speech` accepts `"preprocess": true` (default `false`).

- `false`: `input` reaches the engine unchanged, byte for byte. Dictionaries are **not** applied.
- `true`: the story preprocessor runs on `input` with every enabled dictionary, and the engine receives single-voice text with `[x.xx]` pause tags. The response carries `X-VieNeu-Preprocess: 1`. `max_chars` still applies.
- **Fail-open:** if preprocessing fails, the server logs a warning and speaks the raw `input`; the request does not fail, and `X-VieNeu-Preprocess` is absent.
- The API streams one voice. Speaker voices and per-chunk speed from the preprocessor are not applied here; when some chunk asked for a speed other than 1.0, `X-VieNeu-Ignored` lists `speed`. Use Script Lab or the CLI for multi-voice and speed.

### Numeric pause tags `[x.xx]`

Any text sent to the v3 Turbo engine (API, SDK `infer`/`infer_stream`/batch) may contain pause tags:

- Syntax: one or two integer digits, optional decimals up to three places, optional `s`: `[0.5]`, `[1.25]`, `[2s]`, `[ 0.35 ]`.
- Range: **0 to 5 seconds**. Larger values are clamped to 5 s. Adjacent tags separated only by spaces add up into one pause (`[0.3] [0.5]` → 0.8 s, still clamped at 5 s).
- Tags are never spoken. Other bracket text (`[abc]`, `[cười]`) is not a pause tag and keeps its old meaning (emotion cues). A tag inside `<en>…</en>` stays text.
- **Leading and trailing tags are exact:** that much silence is added before the first audio or after the last. A text made only of tags returns pure silence of that length.
- **Tags between chunks are a minimum:** the joiner measures the natural silence already at the end of the previous chunk and the start of the next, and pads only up to the requested length. A voice with a long natural tail can therefore pause longer than the tag says.
- Text without tags produces the same chunks and gaps as before.
- Paths that cannot carry silence (Gradio's `normalize_to_chunks_v3`, older v1/v2 chunkers) strip tags and treat their position as a sentence boundary.

## 6. Dictionaries

Dictionaries are global: every **enabled** dictionary applies to every preprocessed request (API with `preprocess=true`, Script Lab, preview). Plain API requests never use them.

### JSON format (`vieneu-dictionary/1`)

```json
{
  "format": "vieneu-dictionary/1",
  "name": "Kỳ huyễn: Hogwarts",
  "kind": "name",
  "enabled": true,
  "description": "Tên riêng thế giới Harry Potter.",
  "entries": [
    {"term": "Hogwarts", "replacement": "Hốc-goát", "mode": "phonetic", "case_sensitive": false, "note": ""},
    {"term": "Scotland", "replacement": "", "mode": "en", "case_sensitive": false, "note": "read in English"},
    {"term": "VTV", "replacement": "vê-tê-vê", "mode": "phonetic", "case_sensitive": true, "note": ""}
  ]
}
```

| Field | Rule |
|---|---|
| `format` | Must be `vieneu-dictionary/1`. |
| `name` | 1–80 characters, unique (case-insensitive) in the database. |
| `kind` | `english`, `term` or `name`. When two enabled dictionaries define the same term, `name` wins over `term`, which wins over `english`; ties go to the dictionary name in alphabetical order. |
| `enabled` | Boolean, default `true`. |
| `description` | String, optional. |
| `entries` | List, at most 20 000. |
| `entries[].term` | 1–80 characters, no duplicates inside one file (case-insensitive unless `case_sensitive`). |
| `entries[].mode` | `phonetic` (default): replace by `replacement`. `en`: keep the term and wrap it in `<en>…</en>` so it is read in English. |
| `entries[].replacement` | Up to 200 characters; required for `phonetic`. Must not contain `[`, `]`, `<|`, `|>` or any `<…>` tag. |
| `entries[].case_sensitive` | Boolean, default `false`. Use `true` for acronyms. |
| `entries[].note` | String, optional. |

Broken JSON is reported with its position, for example `Invalid JSON at line 7, column 12: Expecting ',' delimiter`. Field errors name the path, for example `entries[3].replacement: required for phonetic mode`. The whole file is rejected; nothing is imported partially.

### How replacement works

- Terms are matched literally (symbols such as `C++`, `C#`, `.NET` are safe), longest term first, with word boundaries on sides that end in a letter or digit.
- A lower-case term matched at the start of a sentence keeps the capital in the replacement.
- Text inside `<en>…</en>`, `[…]` and `<|…|>` is never changed.
- After the lexicon, any leftover ALL-CAPS word of at least 4 letters becomes Title Case (`GRYFFINDOR` → `Gryffindor`), so shouted words are not spelled out.

### Import modes

| Mode | Effect |
|---|---|
| `new` | Creates a dictionary (optional name override). Fails if the name exists. |
| `merge` | Adds new terms to the chosen dictionary and overwrites terms that already exist. |
| `replace` | Deletes every entry of the chosen dictionary, then inserts the file's entries. |

The dictionary's own name, kind and status are not changed by `merge` or `replace`.

### Seed dictionaries

Shipped in `src/vieneu_admin/seed/`, all enabled on a fresh database:

| File | Name | Kind |
|---|---|---|
| `abbreviations.json` | Từ viết tắt | term |
| `business-finance.json` | Kinh doanh và tài chính | term |
| `english-common.json` | Tiếng Anh thông dụng | english |
| `fantasy-ash-land.json` | Kỳ huyễn: Vùng Đất Tro Tàn | name |
| `fantasy-hogwarts.json` | Kỳ huyễn: Hogwarts | name |
| `it-terms.json` | Thuật ngữ công nghệ | term |
| `medical.json` | Y tế | term |

The two fantasy dictionaries are enabled too, for story demos; disable them if fictional names must not affect general text. Spellings are written for sea-g2p and need a listening check; fix a wrong one in the app (section 5 of the User guide) and export the dictionary to keep the fix.

## 7. Story preprocessor

The preprocessor implements `docs/tts-specs/tts-specs-v1.md` in five stages (`src/vieneu_preprocess/pipeline.py`):

| Stage | Module | Work |
|---|---|---|
| 1 Sanitize | `sanitizer.py` | Unify punctuation, drop chapter metadata, normalize scene breaks to `***`, recover a lost drop-cap first letter. |
| 2 Segment | `dialogue_parser.py`, `speaker_attribution.py`, `inner_voice_detector.py` | Split narration, dialogue and inner voice; attribute speakers from dialogue tags; guard embedded quotes. |
| 3 Prosody | `prosody_annotator.py`, `prosody_clause_splitter.py` | Pause before/after each chunk by rule P-01…P-14, countdown ladder, shout normalization, emotion tags and speed. |
| 4 Lexicon | `lexicon_mapper.py` | Apply the dictionaries (section 6). |
| 5 Export | `exporters.py` | Formatted script (spec §5.2), chunk JSON (spec §5.3), tagged text for the API. |

Every duration, threshold and keyword lives in [`src/vieneu_preprocess/config/pause_rules.yaml`](../src/vieneu_preprocess/config/pause_rules.yaml); the code holds no numbers of its own. A custom YAML passed with `--rules` (CLI) is deep-merged over it: mappings merge, lists are replaced.

Rule table (values are in the YAML, keys in brackets):

| Code | Situation | YAML key |
|---|---|---|
| P-01 / P-02 / P-03 | Sentence end, short / standard / long narration | `pauses.p01_…`, `p02_…`, `p03_…`, `thresholds.*` |
| P-04 | Emphatic short sentence at a paragraph edge | `pauses.p04_emphatic_short` |
| P-05 | Countdown run of short sentences | `countdown.ladder` |
| P-06 | `?`, `!`, `?!` endings | `pauses.p06_question_exclaim` |
| P-07 | Standalone shout / roll call | `pauses.p07_shout_before`, `p07_shout_after` |
| P-08 / P-09 | Dash pairs and dash tails | `pauses.p08_…`, `p09_dash_tail` |
| P-10 | Breath after a long clause | `pauses.p10_long_clause_breath` |
| P-11 / P-12 | Dialogue / inner-voice boundaries | `pauses.p11_…`, `p12_inner_voice` |
| P-13 / P-14 | Paragraph and scene end | `pauses.p13_paragraph`, `p14_scene` |

**Between two chunks** the effective pause is `max(previous pause_after, next pause_before)`, so a boundary is never paused twice.

**Speakers and cast hints.** Speakers come from dialogue tags (`… Hagrid nói.`), pronouns resolve to the last named subject, and unattributed lines get `speakers.unknown_label` ("Nhân vật"). Story-specific hints are **not** part of the default rules: `speakers.aliases` is empty and `speakers.roll_call_speaker` is blank. For the Hogwarts sample, the hints that map "chiếc nón" to "Nón Phân Loại" and roll-call lines to "McGonagall" live in the test fixture `tests/fixtures/preprocess/dracaena_cast_rules.yaml`; pass such a file with `--rules` to get the same speakers. Script Lab and the API use the default rules only.

**Speed.** Chunk speed (for example 0.92 for countdowns) is applied only by Script Lab and the CLI, by **resampling**: the audio plays faster or slower like a tape, so **pitch shifts with speed**. Pause tags inside a sped-up group are pre-scaled so they keep their length. The streaming API ignores speed (section 5).

**Fail-open.** `vieneu_preprocess.preprocess_safely` never raises on bad input: it returns the raw text and the error, which the API logs.

## 8. Command line tools

### `vieneu-preprocess`

```bash
uv run vieneu-preprocess INPUT [--out DIR] [--format script|json|both] \
    [--dict FILE ...] [--rules FILE] [--render --voice NAME]
```

- `INPUT`: a `.md`, `.txt`, `.html` or `.htm` file, or a folder (every such file, in name order, numbered as chapters).
- Output (default `<input folder>/preprocessed/`): `<name>.script.txt` and/or `<name>.json`; with `--render`, also `<name>.wav` (48 kHz) rendered with the local model, per-chunk voice and speed applied.
- `--dict`: dictionary JSON files to use. The CLI does **not** read the admin database; export the dictionaries first (`python -m vieneu_admin export-dicts DIR`) and pass them here.
- `--rules`: YAML merged over the default rules, for example a cast-hints file.
- `--voice`: voice for chunks without one.

### `python -m vieneu_admin`

```bash
uv run python -m vieneu_admin [--db PATH] create-admin USER      # prompts for the password twice
uv run python -m vieneu_admin [--db PATH] reset-password USER    # also ends the user's sessions
uv run python -m vieneu_admin [--db PATH] export-dicts DIR       # every dictionary -> DIR/<slug>.json
uv run python -m vieneu_admin [--db PATH] import-dict FILE [--mode new|merge|replace]
```

`--db` defaults to `VIENEU_ADMIN_DB`, then `vieneu_data/admin.sqlite3`. `import-dict --mode merge|replace` targets the dictionary with the same name and creates it when missing. Exit codes: `0` success, `1` command error, `2` database cannot be opened, `130` aborted. In Docker, run them inside the container: `docker compose -f docker/docker-compose.yml --profile api-gpu exec api-gpu python -m vieneu_admin create-admin admin`.

## 9. Security notes

- **Passwords:** scrypt (N=2^14, r=8, p=1, 16-byte salt). Unknown usernames cost the same time as known ones.
- **Login lockout:** in memory, per (username, client IP): 5 failures in 5 minutes. A restart clears it. Keying on the pair means an attacker cannot lock the real admin out from another address. The client IP is the TCP peer unless the request comes from an address in `FORWARDED_ALLOW_IPS`; without that setting behind a proxy, all users share the proxy's IP and the lockout cannot tell them apart.
- **Sessions:** random 256-bit token in an `HttpOnly`, `SameSite=Lax` cookie (`vieneu_session`), `Secure` with `VIENEU_COOKIE_SECURE=1` or HTTPS; only the SHA-256 is stored. Logout, password change, password reset and disabling a user end sessions.
- **CSRF:** signed double-submit tokens on every `POST`, including `/login`. Anonymous pages create no database rows.
- **API keys:** `vn_` + 256 random bits, shown once, stored as SHA-256 and looked up by hash with a constant-time compare. `last_used_at` is updated at most once a minute.
- **Headers:** `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin` and a Content-Security-Policy on admin pages.
- **Output escaping:** Jinja2 autoescape for all pages; Help renders Markdown with raw HTML disabled, so `<script>` in a doc shows as text.
- **Help files:** `doc` and `lang` are looked up in fixed maps, never joined into a path, so only the four documents can be read.
- **Limits:** admin form bodies over about 5.25 MB are refused (`413`); dictionary uploads 5 MB; Script Lab 50 000 characters to analyse and 3 000 to render; preview 2 000.
- **Dictionary injection:** replacements cannot contain `[`, `]`, `<|`, `|>` or tags, so a dictionary entry cannot add pauses, emotion tokens or engine control tags.
- **Engine sharing:** Script Lab renders go through the same stream slots and queue as the API (`429` when full) and through `infer_stream`, so they never run the GPU graph concurrently with API streams.
- **Exposure:** serve `/admin` over HTTPS when it is reachable from other machines, and set `VIENEU_COOKIE_SECURE=1`.
