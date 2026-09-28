from ingestion.apple_health import daily_aggregates, parse_export

_XML = """<?xml version="1.0"?>
<HealthData>
  <Record type="HKQuantityTypeIdentifierStepCount" startDate="2024-01-15 08:00:00 +0200" value="1200"/>
  <Record type="HKQuantityTypeIdentifierStepCount" startDate="2024-01-15 18:00:00 +0200" value="3000"/>
  <Record type="HKQuantityTypeIdentifierHeartRate" startDate="2024-01-15 08:00:00 +0200" value="60"/>
  <Record type="HKQuantityTypeIdentifierHeartRate" startDate="2024-01-15 08:05:00 +0200" value="80"/>
  <Record type="HKQuantityTypeIdentifierOxygenSaturation" startDate="2024-01-15 08:00:00 +0200" value="0.98"/>
  <Record type="HKCategoryTypeIdentifierIrregularHeartRhythmEvent" startDate="2024-01-15 09:00:00 +0200" value="HKCategoryValueSeverityNotApplicable"/>
</HealthData>"""


def test_parse_samples_and_alerts():
    samples, alerts = parse_export(_XML)
    codes = [s.type_code for s in samples]
    assert codes.count("steps") == 2
    assert codes.count("heart_rate") == 2
    # SpO2 fraction 0.98 → 98%
    spo2 = next(s for s in samples if s.type_code == "spo2")
    assert spo2.value == 98.0
    # irregular rhythm alert
    assert len(alerts) == 1 and alerts[0].alert_type == "irregular_rhythm"
    assert alerts[0].reliability == "consumer_grade"


def test_daily_aggregates():
    samples, _ = parse_export(_XML)
    agg = {a["type_code"]: a for a in daily_aggregates(samples)}
    assert agg["steps"]["value"] == 4200 and agg["steps"]["method"] == "sum"    # sum
    assert agg["heart_rate"]["value"] == 70.0 and agg["heart_rate"]["method"] == "avg"  # average
