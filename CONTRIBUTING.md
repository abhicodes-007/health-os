# Contributing to health-os

Thanks for your interest! Bug reports, ideas and pull requests are welcome.

## Development setup

```bash
cp .env.example .env          # set passwords
docker compose up -d          # Postgres 16
uv sync --extra dev
uv run alembic upgrade head
uv run python -m seed.load
```

Tests:

```bash
make test-unit         # pure unit tests, no database needed
make test              # everything (integration tests use a throwaway <db>_test database)
uv run ruff check .
```

New tests that need the database should use the `conn` / `user_id` fixtures (they are marked
`integration` automatically) or set `pytestmark = pytest.mark.integration`.

## Writing an importer

Store observations through `core.services.ingest_observation` (or `stage_panel` for lab panels),
not with raw `INSERT`s: that is where names are mapped, units converted and critical values
checked. A row without `value_canonical` is invisible to trends and analytics (#11). If you
already imported data directly, `python -m scripts.recompute_canonical` fills it in; the weekly
report's `approved_without_canonical` should stay at 0.

## Privacy — no real medical data

Never include real medical data (yours or anyone else's) in issues, pull requests, test
fixtures, screenshots or logs. Use synthetic values only.

## Contributor License Agreement (CLA)

health-os is licensed under AGPL-3.0-or-later, and the author also offers it under separate
commercial licenses. To keep that possible, every contribution is made under these terms.
By submitting a pull request, patch or other contribution ("Contribution"), you agree that:

1. **Origin.** The Contribution is your original work, or you otherwise have the right to submit
   it under these terms (Developer Certificate of Origin, <https://developercertificate.org/>).
   Please sign off your commits: `git commit -s`.
2. **License to the project.** Your Contribution is published under AGPL-3.0-or-later.
3. **License to the author.** You also grant the project author (GitHub: @andronaft) a perpetual,
   worldwide, non-exclusive, royalty-free, irrevocable license to use, modify, sublicense and
   distribute your Contribution under any license terms, including commercial and proprietary
   licenses, and to relicense the project in the future.
4. **You keep your copyright.** This is a license, not a transfer of ownership — you remain free
   to use your own Contribution however you like.
5. **No warranty.** Contributions are provided "as is", without warranties of any kind.

If you cannot agree to these terms, please open an issue describing the change instead.
