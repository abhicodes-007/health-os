from safety.narrative_flags import is_critical, scan


def _cats(text):
    return {f.category for f in scan(text)}


def test_malignancy_suspicion_uk():
    assert is_critical("Утворення правої молочної залози, підозра на малігнізацію")
    cats = _cats("підозра на малігнізацію")
    assert "malignancy" in cats and "suspicion" in cats


def test_birads_4_5():
    assert is_critical("BI-RADS 4")
    assert is_critical("bi rads 5")
    assert not is_critical("BI-RADS 2")  # 2 — not critical


def test_aneurysm():
    assert is_critical("Аневризма черевної аорти 5 см")


def test_urgent_recommendation():
    assert is_critical("Рекомендовано терміново дообстеження")
    assert is_critical("cito!")


def test_russian_variants():
    assert is_critical("подозрение на злокачественное образование")
    assert is_critical("объемное образование печени")


def test_vascular_emergency():
    assert is_critical("ознаки тромбоемболії легеневої артерії")


def test_benign_text_is_clean():
    assert not is_critical("Печінка не збільшена, структура однорідна. Патології не виявлено.")
    assert not is_critical("Щитоподібна залоза без вогнищевих змін.")


def test_empty_and_none():
    assert scan(None) == []
    assert scan("") == []
