from safety.interactions import (
    biotin_interference_warning,
    check_paracetamol_load,
    refuse_interaction_query,
)


def test_refusal_is_explicit():
    r = refuse_interaction_query()
    assert "assess drug interactions" in r
    assert "pharmacist" in r or "Drugs.com" in r


def test_paracetamol_within_limit():
    load = check_paracetamol_load([{"name": "Парацетамол", "mg_per_dose": 500, "doses_per_day": 3}])
    assert load.level == "ok"
    assert load.total_mg_per_day == 1500


def test_paracetamol_exceeded_across_products():
    # three OTCs with paracetamol at once — the main real risk
    load = check_paracetamol_load([
        {"name": "Цитрамон", "mg_per_dose": 500, "doses_per_day": 3},
        {"name": "Терафлю", "mg_per_dose": 650, "doses_per_day": 3},
        {"name": "Панадол", "mg_per_dose": 500, "doses_per_day": 4},
    ])
    assert load.level == "exceeded"
    assert load.total_mg_per_day > 4000
    assert len(load.products) == 3


def test_paracetamol_caution_band():
    load = check_paracetamol_load([{"name": "Панадол", "mg_per_dose": 1000, "doses_per_day": 3}])
    assert load.level == "caution"  # 3000 mg


def test_biotin_warning_for_tsh():
    w = biotin_interference_warning(taking_biotin=True, planned_test_codes=["tsh", "glucose"])
    assert w and "tsh" in w


def test_biotin_no_warning_without_biotin():
    assert biotin_interference_warning(False, ["tsh"]) is None
    assert biotin_interference_warning(True, ["glucose"]) is None
