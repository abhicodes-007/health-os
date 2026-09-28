from ingestion.confidence import normalize_printed_flag, score


def test_flag_normalization():
    assert normalize_printed_flag("H") == "high"
    assert normalize_printed_flag("↓") == "low"
    assert normalize_printed_flag("N") == "normal"
    assert normalize_printed_flag("") is None


def test_high_confidence_when_flag_matches():
    r = score(printed_flag="H", computed_status="high", conversion_ok=True)
    assert r.score == 1.0 and not r.needs_review and r.flags == []


def test_flag_mismatch_triggers_review():
    # the form says ↑, but the computation is normal → suspected extraction error
    r = score(printed_flag="H", computed_status="normal", conversion_ok=True)
    assert r.needs_review and "flag_mismatch" in r.flags and r.score <= 0.4


def test_unit_gate_low_confidence():
    r = score(printed_flag=None, computed_status=None, conversion_ok=False)
    assert r.needs_review and "unit_gate" in r.flags


def test_no_printed_flag_lowers_but_not_review():
    r = score(printed_flag=None, computed_status="normal", conversion_ok=True)
    assert "no_printed_flag" in r.flags and not r.needs_review


def test_learned_mapping_flagged():
    r = score(printed_flag="H", computed_status="high", conversion_ok=True, learned_mapping=True)
    assert r.needs_review and "learned_mapping" in r.flags


def test_critical_not_compared_to_flag():
    # critical is always on review regardless of the printed flag
    r = score(printed_flag="N", computed_status="critical", conversion_ok=True)
    assert "flag_mismatch" not in r.flags
