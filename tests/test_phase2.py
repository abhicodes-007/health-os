from core.dedup import find_duplicate, jaccard
from core.qualitative import normalize_qualitative, parse_titer


# --- qualitative (integration: seeded database) ---
def test_qualitative_negative_ru(conn):
    r = normalize_qualitative("не обнаружено", conn)
    assert r.canonical == "negative" and r.ordinal_rank == 0


def test_qualitative_positive_uk(conn):
    r = normalize_qualitative("виявлено", conn)
    assert r.canonical == "positive" and r.ordinal_rank == 3


def test_qualitative_unknown(conn):
    assert normalize_qualitative("щось незрозуміле", conn).canonical is None


def test_titer_parsing():
    assert parse_titer("1:160") == 160
    assert parse_titer("1 : 320") == 320
    assert parse_titer("не титр") is None


def test_titer_via_normalize(conn):
    r = normalize_qualitative("1:160", conn)
    assert r.titer_denominator == 160


# --- dedup (pure) ---
def test_jaccard():
    assert jaccard({"a", "b", "c"}, {"a", "b"}) == 2 / 3
    assert jaccard(set(), set()) == 1.0


def test_find_duplicate_same_date_lab():
    from datetime import date
    existing = [{"panel_id": "p1", "panel_date": date(2024, 3, 1), "facility_id": "f1",
                 "codes": {"glucose", "alt", "ast", "creatinine"}}]
    dup = find_duplicate(date(2024, 3, 1), "f1",
                         {"glucose", "alt", "ast", "urea"}, existing)  # 3/5 = 0.6 <0.7 → not dup
    assert dup is None
    dup2 = find_duplicate(date(2024, 3, 1), "f1",
                          {"glucose", "alt", "ast", "creatinine"}, existing)  # 1.0
    assert dup2 is not None and dup2.jaccard == 1.0


def test_no_duplicate_different_date():
    from datetime import date
    existing = [{"panel_id": "p1", "panel_date": date(2024, 3, 1), "facility_id": "f1",
                 "codes": {"glucose"}}]
    assert find_duplicate(date(2024, 4, 1), "f1", {"glucose"}, existing) is None
