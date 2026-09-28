"""Deterministic safety layer (code, NOT prompts).

These modules don't depend on the LLM and must not fail along with the Anthropic API:
- critical_values: rule-engine for critical numeric values (BEFORE the review queue);
- narrative_flags: classifier of critical narrative findings (ultrasound/MRI/histology).
"""
