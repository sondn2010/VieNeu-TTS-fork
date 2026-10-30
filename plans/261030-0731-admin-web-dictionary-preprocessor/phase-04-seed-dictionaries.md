---
phase: 4
title: "Seed dictionaries"
status: pending
priority: P2
effort: "4h"
dependencies: [1]
---

# Phase 4: Seed dictionaries

## Goal

Ship a ready-to-use set of dictionaries in the phase 1 JSON format, loaded on first start, which the user then verifies by ear.

## Files to Create / Modify

- Create under `src/vieneu_admin/seed/`:
  - `english-common.json` (kind `english`, mode `en`, ≥ 200 entries): everyday and media English that Vietnamese text often embeds (email, online, livestream, deadline, meeting, team, feedback, update, download, smartphone, laptop, website, app, game, check-in, shopping, sale, voucher…).
  - `abbreviations.json` (kind `term`, mode `phonetic`, ≥ 150 entries, `case_sensitive: true`): Vietnamese-read spellings for common acronyms (AI → ây-ai, API → ây-pi-ai, CEO → xi-i-âu, GDP → giê-đê-pê, USB → u-ét-bê, WHO → vê-kép-hát-o, UBND → u-bê-en-đê, THPT → tê-hát-pê-tê, ...). Vietnamese-native acronyms use Vietnamese letter names; international ones use the reading common on VTV.
  - `it-terms.json` (kind `term`, ≥ 80): Docker, Kubernetes, GitHub, Python, JavaScript, backend, frontend, server, database, cloud, DevOps, framework…; use `en` mode where v3 Turbo reads English well, `phonetic` where it does not.
  - `business-finance.json` (kind `term`, ≥ 60): KPI, ROI, startup, marketing, branding, e-commerce, Fintech, stock tickers style terms, VN-Index, IPO…
  - `medical.json` (kind `term`, ≥ 60): COVID-19, vaccine, virus, MRI, CT scan, ICU, ADN/DNA, insulin, paracetamol, đơn vị như mg, ml, mmHg…
  - `fantasy-ash-land.json` (kind `name`, mode `phonetic`): every name from spec §4.4 (`Udûn-gath` → `U-đun gát`, `Gorgûl` → `Go-gun`, `Muzgash` → `Mút-gát`, `Gorgoroth` → `Go-gô-rốt`, `Dorwinion` → `Đo-uy-ni-on`, `Ephel Dúath` → `Ê-phen Đu-át`, `Lugbúrz` → `Lúc-bua`) plus the remaining names in the spec text.
  - `fantasy-hogwarts.json` (kind `name`): spec §4.4 Hogwarts list plus the names used in spec §5 (`Hogwarts` → `Hốc-goát`, `Hagrid` → `Ha-gờ-rít`, `Malfoy` → `Man-phôi`, `Harry` → `Ha-ri`, `Potter` → `Pót-tơ`, `Dracaena` → `Đờ-ra-xê-na`, `Gryffindor` → `Gờ-ríp-phin-đo`, `Slytherin` → `Sờ-li-thơ-rin`, `McGonagall` → `Mắc-go-na-gôn`, …) and `Scotland` in `en` mode.
- Create: `tests/test_seed_dictionaries.py`.

## Tasks & Steps

- [ ] Write each file with `format`, `name`, `kind`, `enabled: true`, a one-line `description` (Vietnamese), and entries; add a `note` only when a spelling choice is non-obvious.
- [ ] Keep spellings syllable-hyphenated and in standard Vietnamese orthography so sea-g2p reads them as Vietnamese.
- [ ] Avoid terms that are ordinary Vietnamese words when lower-cased (e.g. do not map `TO`, `AN`, `CON`); keep acronyms `case_sensitive: true`.
- [ ] Test: every file loads via `load_dictionary_json`, minimum counts hold, names are unique across files, `merge_lexicon` across all seeds has no conflicting duplicate within the same kind.

## Verification

- `uv run pytest tests/test_seed_dictionaries.py -q`

## Risk / rollback

Pronunciations are unverified by audio; the user listens and corrects them in the web app (export, edit, re-import). Seeds load only into an empty DB, so later edits are never overwritten.
