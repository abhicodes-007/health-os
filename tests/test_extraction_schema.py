from ingestion.schemas import ExtractionResult


def test_multi_entity_extraction_parses():
    # a discharge summary = labs + diagnosis + prescriptions (multi-entity document)
    data = {
        "doc_type": "discharge",
        "panels": [{
            "panel_date": "2024-03-01", "facility": "Synevo",
            "results": [
                {"raw_name": "Холестерол загальний", "value": 5.8, "unit": "mmol/L",
                 "ref_min": 0, "ref_max": 5.2, "printed_flag": "H"},
                {"raw_name": "RW", "value_text": "не виявлено"},
            ],
            "row_count_in_document": 2,
        }],
        "diagnoses": [{"diagnosis_name": "ГЕРХ", "verification_status": "suspected"}],
        "prescriptions": [{"medication_name": "Омепразол", "dose_amount": 20, "dose_unit": "mg"}],
    }
    res = ExtractionResult.model_validate(data)
    assert res.panels[0].results[0].printed_flag == "H"
    assert res.panels[0].results[1].value_text == "не виявлено"
    assert res.diagnoses[0].verification_status == "suspected"
    assert res.prescriptions[0].medication_name == "Омепразол"


def test_empty_extraction_valid():
    res = ExtractionResult.model_validate({})
    assert res.panels == [] and res.diagnoses == []
