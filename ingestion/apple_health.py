"""Apple Health export.xml import (plan 3.9, Phase 3) — a deterministic parser.

export.zip is a CUMULATIVE full snapshot; every import contains all previous samples
→ into device_samples with UNIQUE + ON CONFLICT DO NOTHING (upsert), otherwise baselines double.

device_alert ≠ sample: "possible atrial fibrillation"/irregular rhythm/SpO₂ alert/fall —
event flags for the red-flag logic (reliability marker: consumer_grade, the AI does not over-interpret).

Pure functions over the XML string; DB writes are separate (importers, in Phase 3 in full).
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime
from xml.etree import ElementTree as ET

# HK identifier → (type_code, daily aggregation method)
HK_QUANTITY = {
    "HKQuantityTypeIdentifierHeartRate": ("heart_rate", "avg"),
    "HKQuantityTypeIdentifierRestingHeartRate": ("resting_hr", "avg"),
    "HKQuantityTypeIdentifierStepCount": ("steps", "sum"),
    "HKQuantityTypeIdentifierOxygenSaturation": ("spo2", "avg"),
    "HKQuantityTypeIdentifierBodyMass": ("body_weight", "last"),
    "HKQuantityTypeIdentifierBodyTemperature": ("body_temp", "avg"),
}

# category events → alert type
HK_ALERTS = {
    "HKCategoryTypeIdentifierIrregularHeartRhythmEvent": "irregular_rhythm",
    "HKCategoryTypeIdentifierHighHeartRateEvent": "high_hr",
    "HKCategoryTypeIdentifierLowHeartRateEvent": "low_hr",
}


@dataclass
class Sample:
    type_code: str
    ts: datetime
    value: float


@dataclass
class DeviceAlert:
    alert_type: str
    detected_at: datetime
    reliability: str = "consumer_grade"


def _parse_ts(s: str) -> datetime:
    # Apple format: '2024-01-15 08:30:00 +0200'
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S %z")


def parse_export(xml: str) -> tuple[list[Sample], list[DeviceAlert]]:
    samples: list[Sample] = []
    alerts: list[DeviceAlert] = []
    for _event, el in ET.iterparse(io.StringIO(xml), events=("end",)):
        if el.tag != "Record":
            continue
        rtype = el.get("type")
        start = el.get("startDate")
        if rtype in HK_QUANTITY and start:
            try:
                val = float(el.get("value"))
            except (TypeError, ValueError):
                el.clear()
                continue
            type_code = HK_QUANTITY[rtype][0]
            if type_code == "spo2" and val <= 1.0:   # Apple stores a fraction 0..1
                val *= 100.0
            samples.append(Sample(type_code, _parse_ts(start), val))
        elif rtype in HK_ALERTS and start:
            alerts.append(DeviceAlert(HK_ALERTS[rtype], _parse_ts(start)))
        el.clear()
    return samples, alerts


def daily_aggregates(samples: list[Sample]) -> list[dict]:
    """Daily aggregates (auto-approved into observations). Method is per type_code."""
    agg_method = {tc: m for tc, m in HK_QUANTITY.values()}
    buckets: dict[tuple[str, str], list[float]] = {}
    for s in samples:
        key = (s.type_code, s.ts.date().isoformat())
        buckets.setdefault(key, []).append(s.value)

    out = []
    for (type_code, day), vals in sorted(buckets.items()):
        method = agg_method.get(type_code, "avg")
        if method == "sum":
            value = sum(vals)
        elif method == "last":
            value = vals[-1]
        else:
            value = sum(vals) / len(vals)
        out.append({"type_code": type_code, "day": day,
                    "value": round(value, 3), "n": len(vals), "method": method})
    return out
