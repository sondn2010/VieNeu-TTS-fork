# Brainstorm: Admin web app, dictionaries, and the spec-based story preprocessor

Date: 2026-10-30 · Branch: `main-bkt` · Status: contract accepted, ready for planning

## Outcome

A single FastAPI process serves the existing OpenAI-compatible speech API plus a web app where:

1. An admin manages users, and every user logs in to create and revoke their own API keys. Those keys authenticate `/v1/audio/speech`, `/v1/voices` and `/v1/models`.
2. Admins manage global, toggleable pronunciation dictionaries ("English", "Thuật ngữ chuyên ngành", fantasy names), each importable and exportable as JSON.
3. A preprocessor implementing `docs/tts-specs/tts-specs-v1.md` (sanitizer, dialogue/inner-voice parser, pause and emotion engine, lexicon mapper, two output formatters) is available as an opt-in `preprocess` field on the speech API, as a "Script Lab" page in the web app (paste text, see the tagged script and JSON chunks, listen), and as a batch CLI.
4. A seed dictionary set ships with the app and works on first start.
5. Two Markdown docs, an app-functions reference and a user guide, are rendered inside the web app's Help page from the same files.

## Decisions (user-confirmed)

| Topic | Decision |
|---|---|
| Access model | Admins create and disable users and see all keys. Users self-serve their own keys. Only admins edit dictionaries. |
| Preprocessor delivery | Opt-in `preprocess` field on the API, Script Lab in the web app, and the CLI from spec §6. |
| Dictionary scope | Global named dictionaries with an on/off toggle. All enabled ones apply to every preprocessed request. |
| Stack | FastAPI + Jinja2/HTMX served by the speech-API process. SQLite storage. No Node toolchain. |

## Evidence from inspection

- `apps/openai_speech.py:202` authenticates with one shared `VIENEU_API_KEY` compared via `hmac`. There are no users and no per-key records.
- **Pause tags such as `[0.35]` are not supported by the engine.** `src/vieneu_utils/phonemize_text.py:32` recognizes only `[cười]`, `[thở dài]` and `[hắng giọng]`. Any other bracketed span is phonemized as text, so `[0.35]` would be read aloud. The pauses between chunks today come from three fixed classes (`V3_GAP_SILENCE` in `src/vieneu_utils/core_utils.py:77`: para 0.70 s, sentence 0.50 s, minor 0.30 s). The existing `pause_pad_samples` / `join_audio_chunks` helpers can already insert exact silences.
- `<en>…</en>` is already kept intact by the chunker (`core_utils.py:17`), so lexicon entries can emit it safely.
- `speed` is accepted by the API but ignored (`X-VieNeu-Ignored`). The engine has no speed control.
- The repo has no custom lexicon hook in the v3 Turbo path. `phonemize_with_dict` exists only on the legacy base path (`src/vieneu/base.py:447`).
- Dependencies already include FastAPI, uvicorn, `librosa` and `soundfile`. Password and key hashing can use the stdlib (`hashlib.scrypt`, `secrets`).

## Constraints

- Stay backward compatible. When `preprocess` is unset, requests and audio are identical to today, and `VIENEU_API_KEY` keeps working as a fallback key.
- The core install stays torch-free. New dependencies are limited to Jinja2, `itsdangerous` (session cookies) and `markdown` (Help page), and these could live behind a `vieneu[web]` extra.
- Never store secrets in plain text. Passwords are scrypt-hashed. An API key is shown once, stored as a SHA-256 hash with a visible prefix, and compared in constant time.
- Login uses session cookies with CSRF protection on every state-changing form. The first admin is bootstrapped from an env var or a CLI command, never with a default password.
- The preprocessor is rule-based with no LLM, and stays within the spec's budget of under 20 ms per chapter.
- Back up the SQLite file before any schema migration.

## Non-goals

- Billing, quotas or per-key rate limits. The existing global stream queue stays the only throttle.
- OAuth/SSO, email invites and password-reset email. Admins reset passwords manually.
- Per-user dictionaries (rejected in favor of global ones).
- The LLM annotator mentioned in spec §3 as an optional future mode.
- MP3 encoding. Script Lab renders WAV or FLAC through `soundfile`.
- Retraining or fine-tuning the model.

## Scope of the work

1. **Engine:** numeric pause tags `[x.xx]` (for example 0.1 to 3.0 s) become explicit silences between sub-chunks on the v3 Turbo path, both batch and stream, reusing `pause_pad_samples`. Out-of-range values are clamped. Other bracket behavior does not change.
2. **Preprocessor package:** the five stages from spec §3, rules P-01 to P-14, the emotion and speed table from §4.3, and the six edge cases from §2. Mode 1 produces a tagged script and Mode 2 produces JSON chunks (`speaker`, `voice_preset`, `role_type`, `text`, `speed`, `pause_before_sec`, `pause_after_sec`). Pause durations live in a `pause_rules.yaml` file. Fixtures are the spec's §5 sample input and output.
3. **Runner:** turns JSON chunks into audio by calling `infer` per chunk with that chunk's voice, then joins the pieces with exact silences. Per-chunk `speed` is applied through `librosa` time-stretch, and only when the value is not 1.0.
4. **Web app:** login and logout, Users (admin), API Keys (own keys; admins see all), Dictionaries (CRUD, toggle, JSON import and export, entry search, test-a-sentence preview), Script Lab, Help.
5. **Seed dictionaries:** English loanwords and tech words (wrapped in `<en>`), abbreviations, domain terms (IT, business/finance, medical), and the fantasy names from spec §4.4 (Ash Land, Hogwarts). They load on first start and can be exported to JSON.
6. **Docs:** an app-functions reference and a user guide in `docs/`, rendered by the Help page. README links are updated.

### Dictionary JSON shape (proposed)

```json
{
  "name": "Thuật ngữ IT",
  "kind": "term",
  "enabled": true,
  "entries": [
    {"term": "API", "replacement": "ây-pi-ai", "mode": "phonetic", "case_sensitive": true, "note": ""},
    {"term": "deadline", "replacement": "", "mode": "en", "case_sensitive": false, "note": ""}
  ]
}
```

`kind` is one of `english`, `term` or `name`. `mode: phonetic` replaces the term with the Vietnamese spelling. `mode: en` wraps the term in `<en>…</en>`. Matching is whole-word, longest term first. On import, the user chooses whether entries merge into the existing dictionary or replace it.

## Trade-offs

- **Same process vs a separate admin service.** Mounting the web app on the speech-API process lets key checks read the same SQLite file with no network hop. This assumes a single API instance. It breaks first under multi-replica deploys, where SQLite on local disk is not shared. A future swap to Postgres behind a small repository module would cover that without changing the UI.
- **Engine pause tags vs preprocessor-only JSON.** Supporting `[x.xx]` in the engine makes Mode 1 scripts work everywhere: API, Gradio and SDK. It assumes the chunker can split on tags without hurting prosody. The first failure would be a tag landing mid-phrase in a way that cuts intonation, which the §5 fixture listen-check should catch. Rendering through JSON only avoids touching the engine, but then plain-text clients never get pauses.
- **Time-stretch for `speed`.** Reusing `librosa` adds no new dependency. It assumes small factors (0.90 to 1.08) stay artifact-free. Audible phasing on cloned voices would be the first failure, and the fallback is to ignore speed while still reporting it in the JSON.

Better approaches: none. The recommended direction is the requested one. The repo already has FastAPI, a chunk-silence join and `<en>` handling to build on, with one addition, the pause-tag engine support described above.

## Acceptance criteria

- With a fresh database and the env-bootstrapped admin, the admin can create a user. That user can log in and create a key. A `curl` with that key gets audio from `/v1/audio/speech`. After the key is revoked, the same request returns 401. The legacy `VIENEU_API_KEY` still works.
- Passwords and keys appear only as hashes in the database. A non-admin gets 403 on the user and dictionary admin routes. Forms without a CSRF token are rejected.
- Exporting a dictionary to JSON and importing it into an empty database gives the same entries. Malformed JSON is rejected with a line-level error.
- The seed dictionaries exist after first start, and preprocessing the spec §5.1 input applies them (for example `Hogwarts → Hốc-goát`, `Slytherin → Sờ-li-thơ-rin`).
- Running the preprocessor on spec §5.1 matches the structure of §5.2 and §5.3 in unit tests: speaker turns, inner-voice split, progressive countdown pauses, the shout normalizer and the drop-cap fix.
- `[0.5]` in API input produces about 0.5 s of silence and is never spoken. A request without `preprocess` produces the same chunks as before (regression test).
- The Help page renders both docs, and the Markdown files in `docs/` are the only source.
- The existing test suite passes, and new tests cover auth, keys, dictionaries, the preprocessor rules and pause tags.

## Resolved follow-ups (2026-10-30)

1. Doc language: both docs ship in English and Vietnamese (`*.md` + `*.vi.md`), following the repo convention. The Help page offers an EN/VI switch.
2. Seed dictionary spellings: Claude writes them in full, and the user verifies them by ear. No release gate inside this delivery.
