"""Extraction contract (plan 4.4) — a Pydantic schema for a multi-entity document.

Real documents are multi-entity: a discharge summary = labs + diagnoses + prescriptions; a photo
with two forms. The extractor (an LLM in an interactive MCP client OR a batch API in
Phase 2) returns EXACTLY this structure — structured output, no tools (injection is caught by
review, it won't drive the agent).

Along with the values, the form's reference range and the printed flag (↑/↓/H/L) are extracted —
needed by the computed confidence (printed-flag vs computed-status mismatch → review).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedLabResult(BaseModel):
    raw_name: str = Field(..., description="observation name as printed on the form")
    value: float | None = None
    unit: str | None = None
    ref_min: float | None = None
    ref_max: float | None = None
    value_text: str | None = Field(None, description="for qualitative results: e.g. 'not detected', titer '1:160'")
    printed_flag: str | None = Field(None, description="printed flag from the form: ↑/↓/H/L/N")


class ExtractedPanel(BaseModel):
    panel_date: str = Field(..., description="form date YYYY-MM-DD")
    panel_type: str | None = None
    facility: str | None = None
    results: list[ExtractedLabResult] = []
    row_count_in_document: int | None = Field(
        None, description="how many observation rows are on the form — for panel completeness")


class ExtractedDiagnosis(BaseModel):
    diagnosis_name: str
    icd10_code: str | None = None
    diagnosed_at: str | None = None
    clinical_status: str | None = "active"
    verification_status: str | None = Field(
        "confirmed", description="suspected/differential/provisional/confirmed/refuted")


class ExtractedPrescription(BaseModel):
    medication_name: str
    dose_amount: float | None = None
    dose_unit: str | None = None
    times_per_day: float | None = None
    product_type: str | None = "prescription"


class ExtractedVaccination(BaseModel):
    vaccine_name: str
    disease: str | None = None
    vaccination_date: str | None = None


class ExtractionResult(BaseModel):
    """What the extractor returns from one document (may be several entities at once)."""
    doc_type: str | None = None
    panels: list[ExtractedPanel] = []
    diagnoses: list[ExtractedDiagnosis] = []
    prescriptions: list[ExtractedPrescription] = []
    vaccinations: list[ExtractedVaccination] = []
    narrative_text: str | None = Field(
        None, description="ultrasound/MRI/histology conclusion — for the narrative critical classifier")
