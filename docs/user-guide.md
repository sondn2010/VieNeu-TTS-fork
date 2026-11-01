# User guide

How to use the VieNeu admin web app and the speech API with API keys, dictionaries and the story preprocessor. Every route, limit and setting is listed in the **Web admin functions** reference (Help → Web admin functions, file `docs/web-admin-functions.md`). Vietnamese version: `docs/user-guide.vi.md`.

> **Before you upgrade an existing server.** With the admin app on (the default), the speech API answers `401` to every call without a valid key, even before any key exists. Create a key first, or set `VIENEU_ADMIN=0` to keep the old keyless API. A fresh database also needs `VIENEU_ADMIN_USER` and `VIENEU_ADMIN_PASSWORD` on the first start, or the server stops with an error.

## 1. Start the server and log in

### First start

```bash
# From the repository
VIENEU_ADMIN_USER=admin VIENEU_ADMIN_PASSWORD='change-me-please' uv run python -m apps.openai_speech
# or, with the Makefile
VIENEU_ADMIN_USER=admin VIENEU_ADMIN_PASSWORD='change-me-please' make api
```

Docker: put the two variables in `docker/.env` (or export them in the shell), then start a profile:

```bash
docker compose -f docker/docker-compose.yml --profile api-gpu up   # or --profile api-cpu
```

The database lives in the `vieneu_data` volume, so the variables are only needed the first time on a new volume. Once an admin exists they are ignored, and changing them does not change the password.

Instead of environment variables you can create the admin with the CLI before the first start:

```bash
uv run python -m vieneu_admin create-admin admin      # asks for the password twice
```

### Log in

1. Open `http://<host>:8000/admin` (`http://<host>:8000/` redirects there).
2. Enter the username and password. Usernames are 3–40 characters (letters, digits, `.`, `_`, `-`); passwords at least 8 characters.
3. After 5 wrong passwords for the same username from the same address within 5 minutes, that username is locked for a few minutes on that address.

The dashboard shows how many active keys you have, which dictionaries are enabled, and whether the speech engine is loaded.

### Change your password

**Change password** (top menu) → enter the current password and the new one twice. Your other sessions (other browsers, other devices) are signed out; this one stays logged in.

## 2. API keys

### Create a key

1. **API keys** → type a name that tells you where the key is used (for example `laptop` or `bot-prod`) → **Create key**.
2. The full key (`vn_…`) appears **once**. Copy it now; the list later shows only its first characters. If you lose it, revoke it and create a new one.

### Revoke a key

**API keys** → **Revoke** on the key's row. Calls with that key get `401` immediately. You can revoke only your own keys; an admin sees and can revoke everyone's.

## 3. Call the speech API

The examples use a key in the shell variable `VIENEU_KEY`.

### curl

```bash
export VIENEU_KEY=vn_your_key_here

# Plain text, WAV file
curl -s http://localhost:8000/v1/audio/speech \
  -H "Authorization: Bearer $VIENEU_KEY" -H "Content-Type: application/json" \
  -d '{"model": "vieneu-v3-turbo", "voice": "Mai Anh", "input": "Xin chào các bạn.", "response_format": "wav"}' \
  -o hello.wav

# Explicit pauses: 0.5 s before, 0.8 s between, 1 s after
curl -s http://localhost:8000/v1/audio/speech \
  -H "Authorization: Bearer $VIENEU_KEY" -H "Content-Type: application/json" \
  -d '{"input": "[0.5] Một, hai. [0.8] Ba! [1]", "response_format": "wav"}' -o pauses.wav

# Story text through the preprocessor and the enabled dictionaries
curl -s -D - http://localhost:8000/v1/audio/speech \
  -H "Authorization: Bearer $VIENEU_KEY" -H "Content-Type: application/json" \
  -d '{"input": "Tòa lâu đài Hogwarts hiện ra. \"Chào mừng các con,\" McGonagall nói.", "preprocess": true, "response_format": "wav"}' \
  -o story.wav
```

The third call prints the response headers: `X-VieNeu-Preprocess: 1` means the preprocessor was applied. When it is missing, preprocessing failed and the raw text was spoken (the server log says why).

### OpenAI SDK (Python)

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="vn_your_key_here")

# Plain request
with client.audio.speech.with_streaming_response.create(
    model="vieneu-v3-turbo", voice="Mai Anh", input="Xin chào các bạn.", response_format="wav",
) as r:
    r.stream_to_file("hello.wav")

# Story text through the preprocessor: send the extra field with extra_body
with client.audio.speech.with_streaming_response.create(
    model="vieneu-v3-turbo", voice="Mai Anh", response_format="wav",
    input="Tòa lâu đài Hogwarts hiện ra. \"Chào mừng các con,\" McGonagall nói.",
    extra_body={"preprocess": True},
) as r:
    r.stream_to_file("story.wav")
```

### What to expect

- **Pause tags** `[x.xx]` work in every request, with or without `preprocess`: 0 to 5 seconds, larger values become 5 s, they are never read aloud. A pause at the very start or end of the text is exact. A pause between two sentences is a **minimum**: if the voice already leaves a natural silence there, the gap can be a little longer than the tag.
- **`preprocess: true`** adds pauses by story rules, applies every enabled dictionary, and reads the whole text with one voice. Speaker voices and per-chunk speed are ignored on the API (header `X-VieNeu-Ignored: speed`); use Script Lab for those.
- **Without `preprocess`**, dictionaries are not applied and the text reaches the engine unchanged.

## 4. Script Lab

Script Lab turns a story into a TTS script and lets you listen to a short passage.

1. **Script Lab** → paste a chapter or a passage (up to 50 000 characters) → **Analyse**.
2. Read the result:
   - **Script**: one line per speaker turn, `Speaker: text [0.35] …`, with `// Phân cảnh` comments at scene breaks. Check that each line belongs to the right speaker and that pauses sit where you expect.
   - **JSON**: one object per chunk (`speaker`, `role_type`, `text`, `speed`, `pause_before_sec`, `pause_after_sec`, `voice_preset`, `temperature`). **Download JSON** saves it.
   - **Tagged text**: the single-voice text the API would speak with `preprocess: true`.
3. Map voices: in **Render preview**, choose a voice for each speaker (`default` uses the engine's default voice).
4. Choose **WAV** (default) or **FLAC** and click **Render audio**. Rendering is available for texts up to **3 000 characters**; for longer texts the page tells you to use the CLI.
5. Listen in the player, or click **Download WAV/FLAC**.

Notes:

- Only one render per session runs at a time. Renders share the engine with API users, so a busy server answers "server busy" (`429`); try again shortly.
- Chunk speed is applied by resampling, so a slower chunk also sounds slightly lower, a faster one slightly higher.
- Speakers come from dialogue tags such as `… Hagrid nói.` Lines without a tag are labelled "Nhân vật". The default rules contain no story-specific cast hints; for example, the Hogwarts sample needs the hints in `tests/fixtures/preprocess/dracaena_cast_rules.yaml` (via the CLI `--rules`) to label "Nón Phân Loại" and "McGonagall".
- The last analysis and audio are kept in server memory only; download what you want to keep.

### Whole chapters: the CLI

```bash
# Export the dictionaries from the database, then preprocess a folder of chapters
uv run python -m vieneu_admin export-dicts dicts/
uv run vieneu-preprocess chapters/ --dict dicts/*.json --out out/
# Also render audio with the local model (one WAV per chapter), with optional cast hints
uv run vieneu-preprocess chapters/chapter-01.md --dict dicts/*.json --rules cast.yaml --render --voice "Mai Anh"
```

## 5. Admin tasks

### Users

**Users** (admins only):

- **Create user**: username, password, role (`user` or `admin`). Give the person their password through a safe channel; they can change it after logging in.
- **Role**: promote or demote. **Disable**: the user is signed out and their keys stop working; **Enable** restores both. **Reset password**: sets a new password and signs the user out. **Delete**: removes the account and its keys.
- You cannot demote, disable, reset or delete your own account here, and the last active admin is always protected. Promote a second admin first.

Lost the only admin password? On the server: `uv run python -m vieneu_admin reset-password <admin>`.

### Dictionaries

**Dictionaries** lists every dictionary; each enabled one applies to every preprocessed request. Everyone can browse and export; only admins can change them.

- **New dictionary**: name, kind (`name` for proper names, `term` for terminology and abbreviations, `english` for words read in English), description.
- **Enable/disable**: the toggle on the list. A disabled dictionary is ignored everywhere.
- **Entries**: open a dictionary → **Add** a term with its replacement (for example `Hogwarts` → `Hốc-goát`), mode `phonetic` (replace) or `en` (keep the word, read it in English), and **Case-sensitive** for acronyms. **Edit** and **Delete** work inline. Search finds terms, 50 per page.
- **Rename / describe** and **Delete** are on the dictionary page.

### Import and export

- **Export JSON** on a dictionary downloads a `vieneu-dictionary/1` file. Keep these files in version control or as backups.
- **Import JSON** (max 5 MB):
  - **New**: creates a dictionary (optionally under another name).
  - **Merge into**: adds new terms and overwrites terms that already exist in the chosen dictionary.
  - **Replace entries of**: deletes every entry of the chosen dictionary, then loads the file.
- A broken file is rejected as a whole, with the position of the error, for example `Invalid JSON at line 7, column 12`.

### Test a sentence

**Preview** at the bottom of the **Dictionaries** page: type a sentence (up to 2 000 characters) and pick one dictionary or "all enabled" under **Using**. The result is the tagged text the engine would receive, so you see both the replacements and the pauses. To hear it, paste the same sentence into Script Lab and render it.

### Fix a seed pronunciation

The server ships seven seed dictionaries (abbreviations, business and finance, common English, two fantasy name sets, IT terms, medical), all enabled on a fresh database. Their spellings are a best guess and should be checked by ear.

1. Render a sentence with the word in Script Lab and listen.
2. If it sounds wrong, open the dictionary that holds the term (use its search), click **Edit**, and change the replacement. Write it the way a Vietnamese reader would say it, syllables joined with `-` (for example `Sờ-li-thơ-rin`). For an English word that the engine already reads well, switch the mode to `en` instead.
3. Preview again, render again, listen.
4. **Export JSON** to keep the corrected file. Changes live in the database; the seed files are only read when the database has no dictionaries at all.

## 6. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `401 invalid api key` from `/v1/*` | No `Authorization: Bearer …` header, a typo, a revoked key, or the owner was disabled. With the admin app on, a key is always required: create one at **API keys**, or use `VIENEU_API_KEY`. To return to the keyless API, start with `VIENEU_ADMIN=0`. |
| `401` right after upgrading | Expected: see the note at the top. |
| Server stops at start with "has no active admin account" | Fresh database without an admin. Set `VIENEU_ADMIN_USER` and `VIENEU_ADMIN_PASSWORD` for the first start, run `python -m vieneu_admin create-admin <user>`, or set `VIENEU_ADMIN=0`. In Docker this happens on every new `vieneu_data` volume. |
| `429` on the API or "server busy" in Script Lab | Every stream slot is busy and the queue is full or timed out. Retry after the `Retry-After` delay, or raise `VIENEU_MAX_STREAMS` / `VIENEU_QUEUE` if the hardware allows. |
| "A render is already running." | Your previous Script Lab render has not finished; wait for it. |
| Login page says "Too many failed attempts" | 5 failures for this username from your address within 5 minutes. Wait, or ask an admin to reset the password. If every user is locked at once behind a reverse proxy, set `FORWARDED_ALLOW_IPS` to the proxy address. |
| "Engine not loaded." in Script Lab | The model is not available (still loading, failed, or crashed). Analysis still works; check `GET /health` and the server log, and restart the server if `/health` returns `503`. |
| Help says "This document is not available on this server" | The docs folder is missing. Set `VIENEU_DOCS_DIR` to the folder that contains `user-guide.md` and `web-admin-functions.md` (Docker images copy them to `/workspace/docs`). |
| A bracket in the text does not pause | Only numbers are pause tags (`[0.5]`, `[2s]`, up to two digits before the point). Words in brackets such as `[cười]` are emotion cues, handled as before. A tag inside `<en>…</en>` stays text. |
| A name is pronounced wrongly with `preprocess` | Find the term in the dictionaries (section 5) and fix it. Without `preprocess`, dictionaries are not used. |
| Logged out unexpectedly | Sessions last 12 hours of inactivity; a password change, a reset, or being disabled also signs you out. |
