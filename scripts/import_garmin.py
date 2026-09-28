"""Import daily wellness metrics from a Garmin Connect GDPR dump → observations (Phase 3).

Sources (DI_CONNECT):
  DI-Connect-Aggregator/UDSFile*         — stress, body battery, respiration, intensity, calories
  DI-Connect-Wellness/*healthStatusData* — resting HR, HRV (daily)
  DI-Connect-Wellness/*sleepData*        — sleep phases/duration/score
  DI-Connect-Metrics/MetricsMaxMetData*  — VO2max

Daily aggregates → observations (channel='device', review_status='approved',
time_precision='date'). Idempotent: a previous garmin import is deleted and re-loaded.
Run: python -m scripts.import_garmin "<path to the dump folder>"
"""
from __future__ import annotations

import glob
import json
import os
import sys
from collections import defaultdict

from sqlalchemy import text

from core.db import engine

TODAY = "2026-07-16"  # cut off Garmin's future service ranges


def _load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return []


def collect(root: str) -> dict:
    di = os.path.join(root, "DI_CONNECT")
    daily: dict[tuple[str, str], float] = {}

    def put(date, code, val):
        if val is None or date is None or date > TODAY:
            return
        daily[(date[:10], code)] = round(float(val), 3)

    # UDS: stress / body battery / respiration / intensity / calories
    for f in glob.glob(os.path.join(di, "DI-Connect-Aggregator", "UDSFile*.json")):
        for r in _load(f):
            d = r.get("calendarDate")
            st = next((a for a in r.get("allDayStress", {}).get("aggregatorList", [])
                       if a.get("type") == "TOTAL"), {})
            if st.get("averageStressLevel", -1) >= 0:
                put(d, "stress_avg", st.get("averageStressLevel"))
            bb = {s.get("bodyBatteryStatType"): s.get("statsValue")
                  for s in r.get("bodyBattery", {}).get("bodyBatteryStatList", [])}
            put(d, "body_battery_high", bb.get("HIGHEST"))
            put(d, "body_battery_low", bb.get("LOWEST"))
            resp = r.get("respiration", {}).get("avgWakingRespirationValue")
            put(d, "respiration_avg", resp)
            im = (r.get("moderateIntensityMinutes") or 0) + (r.get("vigorousIntensityMinutes") or 0)
            put(d, "intensity_minutes", im)
            if r.get("activeKilocalories"):
                put(d, "active_calories", r.get("activeKilocalories"))

    # healthStatus: resting HR + HRV
    for f in glob.glob(os.path.join(di, "DI-Connect-Wellness", "*healthStatusData.json")):
        for r in _load(f):
            d = r.get("calendarDate")
            for m in r.get("metrics", []):
                if m.get("type") == "HR" and m.get("value"):
                    put(d, "resting_hr", m["value"])
                elif m.get("type") == "HRV" and m.get("value"):
                    put(d, "hrv", m["value"])

    # sleep: duration / deep / REM / score
    for f in glob.glob(os.path.join(di, "DI-Connect-Wellness", "*sleepData.json")):
        for r in _load(f):
            if not isinstance(r, dict) or "deepSleepSeconds" not in r:
                continue
            d = r.get("calendarDate")
            deep = r.get("deepSleepSeconds") or 0
            light = r.get("lightSleepSeconds") or 0
            rem = r.get("remSleepSeconds") or 0
            total = deep + light + rem
            if total > 0:
                put(d, "sleep_duration", total / 3600)
                put(d, "sleep_deep", deep / 3600)
                put(d, "sleep_rem", rem / 3600)
            sc = r.get("sleepScores") or {}
            overall = (sc.get("overall") or {}).get("value") or sc.get("overallScore")
            put(d, "sleep_score", overall)

    # VO2max (take the max per day across sports)
    vo2: dict[str, float] = {}
    for f in glob.glob(os.path.join(di, "DI-Connect-Metrics", "MetricsMaxMetData*.json")):
        for r in _load(f):
            d, v = r.get("calendarDate"), r.get("vo2MaxValue")
            if d and v:
                vo2[d[:10]] = max(vo2.get(d[:10], 0), v)
    for d, v in vo2.items():
        put(d, "vo2max", v)

    return daily


def main() -> None:
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    daily = collect(root)
    if not daily:
        print("No daily metrics found — check the path to the dump.")
        return
    by_code = defaultdict(int)
    for (_d, code) in daily:
        by_code[code] += 1

    with engine.begin() as conn:
        uid = conn.execute(text("SELECT id FROM users LIMIT 1")).scalar()
        codes = {c for (_d, c) in daily}
        tid = {code: conn.execute(text("SELECT id FROM observation_types WHERE code=:c"),
                                  {"c": code}).scalar() for code in codes}
        # idempotency: remove the previous garmin import
        conn.execute(text(
            """DELETE FROM observations WHERE source_id IN
               (SELECT id FROM ingestion_sources WHERE extracted_by='garmin-import')"""))
        conn.execute(text("DELETE FROM ingestion_sources WHERE extracted_by='garmin-import'"))
        sid = conn.execute(text(
            """INSERT INTO ingestion_sources (user_id, channel, extracted_by, review_status, pipeline_status)
               VALUES (:u,'device','garmin-import','approved','complete') RETURNING id"""),
            {"u": uid}).scalar()
        for (d, code), val in daily.items():
            if tid.get(code) is None:
                continue
            conn.execute(text(
                """INSERT INTO observations (user_id, type_id, effective_at, time_precision,
                       value_numeric, value_canonical, unit, status, review_status, source_id)
                   VALUES (:u,:t, CAST(:d AS timestamptz),'date', :v,:v, NULL, NULL, 'approved', :s)"""),
                {"u": uid, "t": tid[code], "d": d, "v": val, "s": sid})
        total = conn.execute(text(
            "SELECT count(*) FROM observations WHERE source_id=:s"), {"s": sid}).scalar()
        dmin, dmax = conn.execute(text(
            "SELECT min(effective_at)::date, max(effective_at)::date FROM observations WHERE source_id=:s"),
            {"s": sid}).first()
    print(f"Garmin imported: {total} daily markers, {dmin}..{dmax}")
    for code, n in sorted(by_code.items(), key=lambda x: -x[1]):
        print(f"  {code}: {n} days")


if __name__ == "__main__":
    main()
