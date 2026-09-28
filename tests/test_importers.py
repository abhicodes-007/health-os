"""Integration test of the Apple Health importer (committed data, cleanup in finally)."""
import pytest
from sqlalchemy import text

from core.db import engine
from core.services import get_or_create_user
from ingestion.importers import import_apple_health

pytestmark = pytest.mark.integration  # hits the DB via `engine` / MCP tools directly

_XML = """<?xml version="1.0"?>
<HealthData>
  <Record type="HKQuantityTypeIdentifierStepCount" startDate="2024-01-15 08:00:00 +0200" value="1200"/>
  <Record type="HKQuantityTypeIdentifierHeartRate" startDate="2024-01-15 08:00:00 +0200" value="60"/>
  <Record type="HKQuantityTypeIdentifierHeartRate" startDate="2024-01-15 08:05:00 +0200" value="80"/>
  <Record type="HKCategoryTypeIdentifierIrregularHeartRhythmEvent" startDate="2024-01-15 09:00:00 +0200" value="x"/>
</HealthData>"""


class _Fake:
    def __init__(self): self.calls = []
    def __call__(self, t, m): self.calls.append((t, m))


def _cleanup(uid, source_id):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM device_samples WHERE source_id=:s"), {"s": source_id})
        conn.execute(text("DELETE FROM device_alerts WHERE user_id=:u"), {"u": uid})
        conn.execute(text("DELETE FROM observations WHERE source_id=:s"), {"s": source_id})
        conn.execute(text("DELETE FROM ingestion_sources WHERE id=:s"), {"s": source_id})


def test_apple_health_import_end_to_end():
    fake = _Fake()
    with engine.begin() as conn:
        uid = get_or_create_user(conn)
        out = import_apple_health(conn, uid, _XML, alerter=fake)
    sid = out["source_id"]
    try:
        assert out["samples_inserted"] == 3          # 1 step + 2 hr
        assert out["daily_observations"] == 1        # heart_rate daily aggregate (steps has no obs_type)
        assert out["device_alerts"] == 1
        assert len(fake.calls) == 1                   # irregular_rhythm → alert
        with engine.connect() as conn:
            hr = conn.execute(
                text("""SELECT value_canonical FROM observations o
                        JOIN observation_types ot ON ot.id=o.type_id
                        WHERE ot.code='heart_rate' AND o.source_id=:s"""), {"s": sid}
            ).scalar()
            assert float(hr) == 70.0                  # (60+80)/2
    finally:
        _cleanup(uid, sid)


def test_reimport_is_idempotent():
    """Cumulative re-import doesn't double samples (UNIQUE + reused source)."""
    with engine.begin() as conn:
        uid = get_or_create_user(conn)
        out1 = import_apple_health(conn, uid, _XML)
    with engine.begin() as conn:
        out2 = import_apple_health(conn, uid, _XML)
    sid = out1["source_id"]
    try:
        assert out1["source_id"] == out2["source_id"]   # the same channel source
        assert out2["samples_inserted"] == 0            # ON CONFLICT DO NOTHING
    finally:
        _cleanup(uid, sid)
