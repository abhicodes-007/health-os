from datetime import date

from analytics.screening import (
    DUE,
    NOT_YET,
    OVERDUE,
    UP_TO_DATE,
    build_calendar,
)


def _by_code(recs):
    return {r.code: r for r in recs}


def test_male_27_core_recommendations_present():
    recs = _by_code(build_calendar("male", 27))
    # for a 27-year-old male the key ones must be present
    for code in ["bp", "hiv", "hcv", "hbsag_hepb", "tdap", "testicular", "checkup"]:
        assert code in recs
        assert recs[code].status == DUE  # no data → time to do it


def test_not_yet_for_young_male():
    recs = _by_code(build_calendar("male", 27))
    # colonoscopy and PSA — "you don't need this YET"
    assert recs["colonoscopy"].status == NOT_YET
    assert recs["psa"].status == NOT_YET


def test_colonoscopy_due_with_family_history():
    recs = _by_code(build_calendar("male", 30, flags={"family_colorectal_cancer": True}))
    assert recs["colonoscopy"].status == DUE  # family history → needed earlier


def test_testicular_not_applicable_for_female():
    recs = _by_code(build_calendar("female", 27))
    assert "testicular" not in recs
    assert "psa" not in recs


def test_overdue_vs_uptodate_by_last_done():
    today = date(2026, 7, 15)
    recs = _by_code(build_calendar("male", 40, last_done={
        "tdap": date(2010, 1, 1),   # >10 yr ago → overdue
        "bp": date(2026, 3, 1),     # recently → up_to_date
    }, today=today))
    assert recs["tdap"].status == OVERDUE
    assert recs["bp"].status == UP_TO_DATE


def test_one_time_screen_uptodate_once_done():
    recs = _by_code(build_calendar("male", 27, last_done={"hiv": date(2024, 1, 1)}))
    assert recs["hiv"].status == UP_TO_DATE  # one-off, done


def test_audiometry_only_with_exposure():
    assert "audiometry" not in _by_code(build_calendar("male", 27))
    assert "audiometry" in _by_code(
        build_calendar("male", 27, flags={"noise_or_blast_exposure": True})
    )
