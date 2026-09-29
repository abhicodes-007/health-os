# health-os

[![tests](https://github.com/andronaft/health-os/actions/workflows/tests.yml/badge.svg)](https://github.com/andronaft/health-os/actions/workflows/tests.yml)

Personal AI health system: a self-hosted store for your medical data (labs, diagnoses,
medications, device data, food log) with deterministic safety checks and a Claude MCP interface.
The design plan and personal documents are kept privately, outside this repository.

> **Medical disclaimer.** This is not a medical device and does not give medical advice.
> Critical-value alerts and screening reminders are only a signal to contact a doctor —
> never a diagnosis and never a reason to delay care. Use at your own risk.

## Stack

Python 3.13 · PostgreSQL 16 (Docker) · SQLAlchemy · Alembic · FastMCP · FastAPI · aiogram · APScheduler.
pgvector is enabled in Phase 3 (the image already has it), not earlier.

## Structure

```
health-os/
├── docker-compose.yml     # Postgres 16 (pgvector image)
├── alembic.ini
├── migrations/            # Alembic; 0001 = schema v3 (Part 3 of the plan)
├── core/                  # config, db, (Phase 1: models, schemas, services, normalize/)
├── ingestion/             # Phase 1: pipeline (state machine), extractors/, importers/
├── mcp_server/            # Phase 1
├── api/                   # Phase 4 (planned, not yet created)
├── worker/                # APScheduler: recomputation, cron reports, device_samples partitions
├── bot/                   # Phase 4 (aiogram; planned, not yet created)
├── analytics/             # Phase 5
├── safety/                # Phase 1: critical_values, red_flags, crisis — deterministic code
├── evals/                 # Phase 1: golden set + red-team
├── prompts/               # versioned prompts
├── seed/                  # observation_types, synonyms, unit_conversions, reference_ranges
└── data/                  # files, backups (outside git)
```

## Quick start (Phase 0)

```bash
cp .env.example .env          # edit passwords
docker compose up -d          # bring up Postgres 16
uv sync                       # or: python3 -m venv .venv && pip install -e .
uv run alembic upgrade head   # schema v3
uv run python -m seed.load    # marker reference data
```

**Phase 0 criterion:** `docker compose up` → live database; `alembic upgrade head` without errors;
seed loaded; backup→restore test passed; FileVault enabled (`fdesetup status`).

## Tests

```bash
make test              # everything (needs Postgres for the integration part)
make test-unit         # pure unit tests — no database needed
make test-integration  # only tests marked `integration`
```

Tests that need the database carry the `integration` marker — added automatically for tests
using the `conn`/`user_id` fixtures, or via `pytestmark` for modules that use `engine` directly.

Integration tests never touch the working database: `tests/conftest.py` drops and recreates
`<POSTGRES_DB>_test` on the same Postgres server (migrations + seed) on every run.
Override with `TEST_DATABASE_URL` (the database name must end in `_test`).
If Postgres is down, integration tests are skipped; unit tests still run.

## Privacy

- `data/` and `.env` — outside git (see `.gitignore`).
- FileVault is mandatory (otherwise PHI is on disk in plaintext).
- Real medical data to Anthropic — only via the API with commercial/ZDR terms.
- Never put real medical data in issues, PRs or tests — synthetic data only.

## License

[AGPL-3.0-or-later](LICENSE). You may use, modify and fork health-os; if you distribute it or
run a modified version as a network service, you must publish your source under the same license.

Want to use it in a closed-source or commercial product without those obligations? A separate
commercial license is available from the author — reach out via GitHub
([@andronaft](https://github.com/andronaft)).

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) (includes a short CLA).
