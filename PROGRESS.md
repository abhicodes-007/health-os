# Health OS — progress log (archived)

> **Archived.** This is the original phase-by-phase development journal, kept for history and
> no longer updated after the first public release (2026-09-29). Numbers in it (tests, tools,
> tables) are from that time. For the current state see [README.md](README.md) and
> [CHANGELOG.md](CHANGELOG.md). The design plan it refers to is private and not in this repo.

## Locked-in decisions (as implementation went)

| Date | Decision | Details |
|---|---|---|
| 2026-07-15 | **24/7 hosting = Mac** | Starting on the user's Mac. Mini-PC/VPS+Tailscale deferred until a bot/critical alerts are in production (Phase 1+), if the system proves useful. |
| 2026-07-15 | Postgres host port = **5433** (author's machine only) | 5432 is taken by another local Postgres. The default in `.env.example` is 5432. |
| 2026-07-15 | Backup (restic repo + key) | Deferred until the first real analyses are loaded. The database is empty for now. |

---

## Phase 0-lite — demand check (day 1–2, no code) ✅ LAUNCHED
- [x] `health/` created (README, health_summary.md template, usage_log.md, documents/)
- [x] FileVault enabled
- [ ] **user action:** fill in `health/health_summary.md` with your data
- [ ] **user action:** drop analyses into `health/documents/`
- [ ] Live 4 weeks (until ≈2026-08-12), count uses in usage_log.md
- **Kill criterion:** <2 uses/week without self-coercion → don't build the system

## Phase 0 — foundation (1–2 weeks) ✅ CODE READY
- [x] Hosting decision = Mac
- [x] FileVault
- [x] Repo, docker-compose (Postgres 16 pgvector image), pyproject, .env
- [x] worker/ (device_samples partitions)
- [x] Alembic + schema v3 (34 tables) — **validated on a live database**
- [x] Seed: 48 markers, 176 synonyms (uk/ru/en/la), 12 conversions, 16 references, 6 critical thresholds
      (⚠️ provisional — refine against real forms)
- [x] Backup scripts (backup.sh + restore_test.sh, restic)
- [ ] **deferred:** set up the restic repo and run restore_test.sh (until the first real data)
- **Criterion:** docker up → live database ✅; migration+seed ✅; FileVault ✅; hosting decided ✅

## Phase 1 — MCP MVP + eval (3–4 weeks) 🔵 IN PROGRESS
- [x] safety/critical_values.py — critical-values rule-engine (pure fn + DB loader), **8 tests ✅, end-to-end on a live database ✅**
- [x] safety/narrative_flags.py — classifier of critical narrative findings (Bi-RADS/TI-RADS/PI-RADS 4-5, malign*, aneurysm*, cito, thromboembol…), **8 tests ✅**
- [x] Read-only approved-views (v_observations, v_observations_pending, v_medications_current, v_diagnoses, v_allergies) + role health_readonly (statement_timeout=5s) — migration 0002, **filtering verified on a live database ✅**
- [x] normalization (`core/normalize.py`): string canonicalization (lower/ё→е/hyphens/trim) + exact synonym match + analyte-specific conversion + unit gate + compute_status from the form — **tests ✅**
- [x] core services (`core/services.py`): upsert_profile, add_allergy (fail-safe unverified), add_diagnosis (2 status axes), add_medication, ingest_observation (normalization+status+critical rule-engine) — **tests ✅**
- [x] **Whole test suite: 31 green tests** (safety 16 + normalize + services integration), the DB stays clean (transaction with rollback)
- [x] Health Summary (`core/health_summary.py`): deterministic block (profile/allergies with unverified/active diagnoses with verification_status/current meds/exam recency) + mechanical post-validation (counters==COUNT) — **tests ✅**. LLM block (trends) — later, needs the API.
- [x] MCP server (`mcp_server/`): 8 tools (get_health_summary, query_observations with >90-day aggregation, get_timeline, get_medications/diagnoses/allergies, list_pending_reviews, sql_query read-only), reads through approved-views, response limits — **tools.py tests ✅, the server registers 8 tools ✅**. Connection config — mcp_server/README.md.
- [x] **Whole test suite: 38 green tests**, including the critical property: pending does NOT leak into an approved-view.
- [x] **Interactive extraction via Claude Code (WITHOUT an API key)** — MCP write tools (`mcp_server/write_tools.py`): set_profile, record_allergy/diagnosis/medication, **stage_lab_panel** (normalization+critical alerts, lands as pending), **approve_staged_source** (a separate explicit action, guardrail). The cycle: you throw a PDF → the model in the subscription reads it → stage → table → approve. **Full-cycle test stage→review→approve ✅** (14 MCP tools together)
- [x] Fixed along the way: a marker from a form is dated with the panel's date (time_precision='date'), not now()
- [ ] Automatic pipeline (batch, state machine, cron) — needs the Anthropic API (Phase 2+, this is automation without the user's participation)
- [ ] Health Summary LLM block (trends/questions) — can be done interactively via Claude Code too
- [ ] Golden set (needs real documents from the user)
- [x] Minimal critical-alert channel (`safety/alerts.py`): log file + macOS notification + optional bare Telegram sendMessage (generic text, privacy); wired into ingest_observation via an optional alerter — **tests ✅, the real channel verified (log+macos delivered)**
- [x] Narrative critical alerts (`narrative_flags.check_and_alert`) — scan+alert for ultrasound/histology
- [x] A single escalation & silence policy + disclaimer (`safety/policy.py`): versioned red-flags list, list of "when it goes quiet and sends to a doctor", forbidden phrasings, DISCLAIMER — **tests ✅**
- [x] **MCP role hardening:** a separate login role `health_readonly` (READONLY_DATABASE_URL), migration 0003 + scripts/setup_readonly.py; at the DB-privilege level it sees only approved-views+users, while observations/audit_log/staging/critical_thresholds — permission denied, writes — ReadOnlySqlTransaction. **Privilege matrix verified ✅.** sql_query and view read tools → readonly_engine; get_health_summary (post-validation over base tables) and writes → main connection.
- [x] MCP: connected to Claude Code (user scope) + Claude Desktop config ✅ (14 tools)
- [x] **Deterministic safety/analytics pieces (no data/API):**
  - `analytics/screening.py` — screening calendar (profile-dependent, age-gate, "you don't need this yet") + MCP tool get_screening_recommendations
  - `safety/crisis.py` — crisis protocol (keyword uk/ru/en + fixed response 7333/103/112, independent of the API)
  - `safety/interactions.py` — DDI guardrail (refuses to assess interactions) + deterministic total paracetamol across products + biotin-before-TSH
  - **+18 tests; whole suite — 64 green tests; server = 15 MCP tools**
- **Criterion:** analysis PDF → "extracted" → "ok" → "compare with the previous one" correctly; precision ≥98% on the golden set
- **⛔ Kill-gate after 3 months:** ≥2 of 5 criteria failed → Phases 4–6 are cancelled

### What's still left in Phase 1 (needs real data/user actions)
- A real extraction cycle on a form (restart the Claude Code session → drop a PDF)
- Golden set (20–40 real documents + manual labeling) + eval script
- Health Summary LLM block (trends) — interactively via Claude Code

## Phase 5 (advance) — deterministic pieces already started
The screening calendar was done ahead of schedule. Remaining: baselines (rolling mean/σ), trends
(Mann-Kendall), age-gated calculators (SCORE2/ASCVD/FRAX with a refusal for <40), weekly report.

## Phase 2 — Batch import of the archive 🟡 deterministic parts done
- [x] Qualitative values + titers (`core/qualitative.py`, seed 4 values, migration 0004) — tests ✅
- [x] Logical panel dedup (`core/dedup.py`, Jaccard≥0.7 by date+lab) — tests ✅
- [x] Extraction contract (`ingestion/schemas.py`, Pydantic multi-entity) — tests ✅
- [ ] The actual LLM extraction (Batch API) — needs the API; interactively already works via stage_lab_panel
- [ ] ATC drug reference; extractors for ultrasound/discharge summaries/forms 027, 063

## Phase 3 — Trackers + semantic search 🟡 deterministic parts done
- [x] Apple Health export.xml parser (`ingestion/apple_health.py`): samples + daily aggregates
      (sum/avg/last) + device_alerts (irregular_rhythm etc., consumer_grade) — tests ✅
- [x] device_alerts, document_chunks tables (no embedding — until a model is chosen), pgvector on (migration 0004)
- [ ] Writing samples into device_samples (upsert) + search tool — needs importers + choice of an embedding model

## Phase 5 — Analytics 🟡 deterministic parts done
- [x] Baselines/anomalies (`analytics/baselines.py`, rolling mean/σ, z>2, min_n=5) — tests ✅
- [x] Trends (`analytics/trends.py`, Mann-Kendall + OLS slope, pure python) + MCP get_trend — tests ✅
- [x] Age-gated calculators (`analytics/calculators.py`, SCORE2/ASCVD/FRAX refusal for <40 + BMI) — tests ✅
- [x] Screening calendar (done earlier)
- [ ] Correlation engine (block permutation), weekly report with an anxiety budget

**State: 104 green tests, 38 tables, 18 MCP tools.**

### Pushed end-to-end (2026-07-15, second session-wave)
- [x] Computed confidence (`ingestion/confidence.py`): printed flag vs computed status,
      unit gate, learned mapping → score+needs_review; embedded in stage_lab_panel (every row has confidence)
- [x] Logical panel dedup embedded in stage_lab_panel (duplicate_warning in the output)
- [x] **Real Apple Health importer** (`ingestion/importers.py`): XML → device_samples (upsert,
      idempotent re-import) + daily aggregates→observations (idempotent) + device_alerts + alert on irregular_rhythm
- [x] `prepare_doctor_visit` + `get_weekly_report` (deterministic report with system-health metrics:
      pending-queue size, corrected ratio) — MCP tools
- [x] Red-team eval set (`evals/test_red_team.py`): injection+hidden critical finding, critical number despite
      an "all-good" text, unit trick, obfuscated suicide, DDI refusal, paracetamol stacking
- [x] Frozen agent system prompt (`prompts/system_prompt.py`, assembled from policy)

## Phase 4 (bot) / Phase 6 (web) — not started
Bot: aiogram + crisis protocol (crisis.py already ready) + red-flag classifier. May be dropped by the kill-gate.

---

## Technical notes for the next session
- Start the DB: `cd health-os && docker compose up -d` (port 5433)
- Migrations: `.venv/bin/alembic upgrade head`
- Seed: `.venv/bin/python -m seed.load`
- Tests: `.venv/bin/pytest`
- venv is already created in `health-os/.venv/`
