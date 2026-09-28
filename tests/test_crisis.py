from safety.crisis import crisis_response, is_crisis


def test_detects_suicidal_uk_ru_en():
    assert is_crisis("я більше не хочу жити")
    assert is_crisis("думаю покінчити з собою")
    assert is_crisis("хочу умереть, нет смысла")
    assert is_crisis("I want to die")


def test_non_crisis_is_clean():
    assert not is_crisis("сьогодні болить голова і трохи втомився")
    assert not is_crisis("хочу записатись до лікаря")
    assert not is_crisis(None)


def test_response_has_hotlines():
    r = crisis_response()
    assert "7333" in r
    assert "103" in r and "112" in r


def test_response_includes_trusted_contact():
    r = crisis_response(emergency_contact="Мама +380...")
    assert "Мама" in r


def test_response_has_no_analytics_language():
    r = crisis_response().lower()
    assert "trend" not in r and "metric" not in r  # no analytics during a crisis
