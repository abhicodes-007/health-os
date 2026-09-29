"""MCP tool tests. tools.py reads through separate connections (like the real MCP),
so committed data is needed — we clean up in finally."""
import json

import pytest
from sqlalchemy import text

from core.db import engine
from core.services import get_or_create_user, ingest_observation
from mcp_server import tools

pytestmark = pytest.mark.integration  # hits the DB via `engine` / MCP tools directly


def test_sql_query_rejects_writes():
    assert "error" in json.loads(tools.sql_query("UPDATE observations SET status='x'"))
    assert "error" in json.loads(tools.sql_query("DELETE FROM users"))
    assert "error" in json.loads(tools.sql_query("DROP TABLE users"))


def test_sql_query_allows_select():
    out = json.loads(tools.sql_query("SELECT 1 AS one"))
    assert out["rows"][0]["one"] == 1


def test_sql_query_is_read_only_at_db_level():
    # even if the keyword filter let it through — the READ ONLY transaction blocks the write
    out = json.loads(tools.sql_query(
        "WITH x AS (SELECT 1) INSERT INTO users DEFAULT VALUES"
    ))
    assert "error" in out  # rejected (doesn't start with select, or read-only)



def test_sql_query_sees_only_approved_views_without_readonly_url():
    # tests run WITHOUT READONLY_DATABASE_URL, as the owner (a superuser in Docker) — the case
    # that used to expose base tables and server files
    assert "rows" in json.loads(tools.sql_query("SELECT count(*) FROM v_observations"))
    for q in ("SELECT count(*) FROM observations",          # includes pending/unverified rows
              "SELECT count(*) FROM audit_log",
              "SELECT date_of_birth FROM user_profile",
              "SELECT pg_read_file('/etc/hostname')"):      # server files
        out = json.loads(tools.sql_query(q))
        assert "permission denied" in out.get("error", ""), (q, out)

def test_query_observations_roundtrip():
    with engine.begin() as conn:
        uid = get_or_create_user(conn)
        res = ingest_observation(conn, uid, "глюкоза", 5.2, "mmol/L",
                                 ref_min=3.9, ref_max=5.5)
        oid = res.observation_id
        sid = conn.execute(
            text("SELECT source_id FROM observations WHERE id=:i"), {"i": oid}
        ).scalar()
    try:
        out = json.loads(tools.query_observations("glucose", days=30))
        assert any(float(r["value_canonical"]) == 5.2 for r in out["rows"])
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM observations WHERE id=:i"), {"i": oid})
            conn.execute(text("DELETE FROM ingestion_sources WHERE id=:i"), {"i": sid})


def test_pending_not_in_approved_view():
    """A critical value (pending) must NOT leak into v_observations."""
    with engine.begin() as conn:
        uid = get_or_create_user(conn)
        res = ingest_observation(conn, uid, "калій", 6.8, "mmol/L")  # critical → pending
        oid = res.observation_id
        sid = conn.execute(
            text("SELECT source_id FROM observations WHERE id=:i"), {"i": oid}
        ).scalar()
    try:
        approved = json.loads(tools.query_observations("potassium", days=30))
        assert all(float(r["value_canonical"]) != 6.8 for r in approved["rows"])
        pending = json.loads(tools.list_pending_reviews())
        assert any(str(r["id"]) == oid for r in pending)
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM observations WHERE id=:i"), {"i": oid})
            conn.execute(text("DELETE FROM ingestion_sources WHERE id=:i"), {"i": sid})


def test_crisis_resources_tool():
    out = json.loads(tools.crisis_resources("I want to die"))
    assert out["detected_by_keywords"] is True
    assert "112" in out["response"]
    # always returns the resources, even if keywords don't match (false positive > miss)
    assert "112" in json.loads(tools.crisis_resources("I feel off"))["response"]


def test_check_medication_safety_tool():
    out = json.loads(tools.check_medication_safety(
        paracetamol_products=[{"name": "Paracetamol", "mg_per_dose": 1000, "doses_per_day": 5}]))
    assert out["paracetamol"]["level"] == "exceeded"
    assert "interactions" in out
