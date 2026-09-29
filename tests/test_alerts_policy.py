from core.services import ingest_observation
from safety import narrative_flags, policy


class FakeAlerter:
    def __init__(self):
        self.calls = []

    def __call__(self, title, message):
        self.calls.append((title, message))


# --- policy ---
def test_policy_text_contains_key_elements():
    txt = policy.escalation_policy_text()
    assert "103/112" in txt
    assert "testicular torsion" in txt
    assert "Bi-RADS" in txt or "malign" in txt
    assert policy.POLICY_VERSION in txt


def test_disclaimer_nonempty():
    assert "does not replace a doctor" in policy.DISCLAIMER


# --- critical value fires alerter ---
def test_critical_observation_triggers_alerter(conn, user_id):
    fake = FakeAlerter()
    res = ingest_observation(conn, user_id, "калій", 6.8, "mmol/L", alerter=fake)
    assert res.critical is not None
    assert len(fake.calls) == 1
    assert "калій" in fake.calls[0][1] or "potassium" in fake.calls[0][1]


def test_normal_observation_no_alert(conn, user_id):
    fake = FakeAlerter()
    ingest_observation(conn, user_id, "глюкоза", 5.2, "mmol/L",
                       ref_min=3.9, ref_max=5.5, alerter=fake)
    assert fake.calls == []


# --- narrative check_and_alert ---
def test_narrative_alert_on_malignancy():
    fake = FakeAlerter()
    hits = narrative_flags.check_and_alert(
        "Об'ємне утворення, підозра на малігнізацію", source_label="УЗД", alerter=fake
    )
    assert hits
    assert len(fake.calls) == 1
    assert "УЗД" in fake.calls[0][1]


def test_narrative_no_alert_on_clean_text():
    fake = FakeAlerter()
    hits = narrative_flags.check_and_alert("Патології не виявлено.", alerter=fake)
    assert hits == []
    assert fake.calls == []
