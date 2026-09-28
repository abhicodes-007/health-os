"""Monthly device_samples partitions.

Plan (3.9): worker/ creates partitions monthly (cron); the first insert into a
nonexistent partition fails. A default partition already exists (guards against
that failure), but for performance we keep separate monthly ones. In Phase 3 this
job is hooked onto APScheduler.

Manual run: uv run python -m worker.partitions
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import text

from core.db import engine


def _month_bounds(d: date) -> tuple[date, date, str]:
    start = d.replace(day=1)
    end = date(start.year + 1, 1, 1) if start.month == 12 else date(start.year, start.month + 1, 1)
    name = f"device_samples_{start:%Y_%m}"
    return start, end, name


def ensure_partition(d: date) -> str:
    start, end, name = _month_bounds(d)
    with engine.begin() as conn:
        conn.execute(
            text(
                f"CREATE TABLE IF NOT EXISTS {name} PARTITION OF device_samples "
                f"FOR VALUES FROM ('{start:%Y-%m-%d}') TO ('{end:%Y-%m-%d}')"
            )
        )
    return name


def ensure_current_and_next() -> list[str]:
    today = date.today()
    next_month = date(today.year + (today.month == 12), (today.month % 12) + 1, 1)
    return [ensure_partition(today), ensure_partition(next_month)]


if __name__ == "__main__":
    print("Created/existing partitions:", ", ".join(ensure_current_and_next()))
