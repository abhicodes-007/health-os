"""Spanish lab forms map to the catalog (regression: a La Fe report matched ~20 of ~100 rows)."""
from collections import defaultdict

import pytest

from core.normalize import canonicalize, canonicalize_unit, normalize
from seed.data import OBSERVATION_TYPES, SYNONYMS


def test_every_synonym_maps_to_exactly_one_type():
    codes = {t[0] for t in OBSERVATION_TYPES}
    owners = defaultdict(set)
    for code, syns in SYNONYMS.items():
        assert code in codes, code
        for s, _ in syns:
            assert s == canonicalize(s), f"synonym not canonical: {s!r}"
            owners[s].add(code)
    assert not {s: c for s, c in owners.items() if len(c) > 1}


def test_latin_accents_stripped_but_cyrillic_kept():
    assert canonicalize("Fósforo Inorgánico") == "fosforo inorganico"
    assert canonicalize("Йод") == "йод" and canonicalize("Їжак") == "їжак"


@pytest.mark.parametrize("printed,canonical", [
    ("mUI/mL", "mIU/mL"), ("μUI/mL", "uIU/mL"), ("seg", "s"), ("µg/dL", "ug/dL"),
    ("mL/min/1,73m2", "mL/min/1.73m2"),
])
def test_spanish_unit_spellings(printed, canonical):
    assert canonicalize_unit(printed) == canonical


@pytest.mark.parametrize("name,value,unit,code,canon", [
    ("Bilirrubina Total", 2.15, "mg/dL", "total_bilirubin", 36.765),
    ("Bilirrubina Indirecta", 1.55, "mg/dL", "indirect_bilirubin", 26.505),
    ("Fósforo Inorgánico", 4.0, "mg/dL", "phosphorus", 1.2916),
    ("Hierro", 162, "µg/dL", "iron_serum", 29.0142),
    ("Ig A", 7, "mg/dL", "iga", 0.07),
    ("Hemoglobina", 16.8, "g/dL", "hemoglobin", 168.0),
    ("Concentración Hemoglobina Corpuscular Media", 34.9, "g/dL", "mchc", 349.0),
    ("Linfocitos %", 42.2, "%", "lymphocytes_pct", 42.2),
    ("Linfocitos #", 2.82, "x10^3/µL", "lymphocytes_abs", 2.82),
    ("TSH", 1.23, "mU/L", "tsh", 1.23),
    ("Urea", 35, "mg/dL", "urea", 5.8275),
    ("Fibrinógeno Derivado", 244, "mg/dL", "fibrinogen", 2.44),
    ("Hepatitis B Ac Superficie", 215, "mUI/mL", "hbs_ab", 215),
])
def test_la_fe_rows_normalize(conn, name, value, unit, code, canon):
    nr = normalize(name, value, unit, conn)
    assert nr.type_code == code, (name, nr)
    assert nr.value_canonical == pytest.approx(canon, rel=1e-3)


def test_bare_leukocyte_subtype_is_not_guessed(conn):
    # "Linfocitos" alone is used for both % and absolute counts → must not be auto-mapped
    assert normalize("Linfocitos", 2.82, "x10^3/µL", conn).type_code != "lymphocytes_pct"
