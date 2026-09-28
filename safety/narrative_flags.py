"""Classifier of critical NARRATIVE findings (plan 4.5, v3).

The critical-values rule-engine is numeric, but ultrasound/MRI/CT conclusions and histology
are text. A phrase like "mass, suspicion of malignancy / Bi-RADS 4–5 / 5 cm aneurysm /
urgent follow-up recommended" has no numeric trigger and may settle into pending or be
rephrased by the LLM in the summary. This is the same class of false reassurance as
potassium 6.8.

A deterministic keyword/pattern classifier (zero dependencies on the LLM). High-recall:
a false positive a human dismisses is better than a missed malignancy.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# (category, regex). Patterns run over normalized (lowercase) text, uk+ru+en+lat.
_PATTERNS: list[tuple[str, str]] = [
    ("malignancy", r"малігн|злоякісн|озлоякіснен|малигн|злокачествен|malign|carcinom|карцином|сарком|sarcom|метастаз|metastas|неоплаз|neoplas"),
    ("suspicion", r"підозра на|подозрение на|susp(?:ected|icion)|susp\."),
    ("birads", r"bi[-\s]?rads\s*[:\-]?\s*[45]"),
    ("tirads", r"ti[-\s]?rads\s*[:\-]?\s*[45]"),
    ("pirads", r"pi[-\s]?rads\s*[:\-]?\s*[45]"),
    ("aneurysm", r"аневризм|aneurysm"),
    ("urgent", r"рекомендовано терміново|терміново дообстеж|срочно|ургентн|urgent|cito\b|cito!|негайн(?:о|е)\s+звернен"),
    ("acute_vascular", r"тромбоембол|тромбоз|thrombos|embol|інсульт|stroke|інфаркт|infarct"),
    ("mass", r"новоутворен|об'?ємне утворення|объемное образование|пухлин|tumor|tumou?r|вогнищев[еі] утворенн"),
]

_COMPILED = [(name, re.compile(pat, re.IGNORECASE)) for name, pat in _PATTERNS]


@dataclass(frozen=True)
class NarrativeFlag:
    category: str
    matched_text: str


def _normalize(text: str) -> str:
    # ё→е, keep ї/і; collapse extra spaces; lowercase
    text = text.replace("ё", "е").replace("Ё", "Е")
    text = unicodedata.normalize("NFC", text)
    return text.lower()


def scan(text: str | None) -> list[NarrativeFlag]:
    """Returns a list of found critical narrative markers (may be empty)."""
    if not text:
        return []
    norm = _normalize(text)
    hits: list[NarrativeFlag] = []
    for name, rx in _COMPILED:
        m = rx.search(norm)
        if m:
            hits.append(NarrativeFlag(category=name, matched_text=m.group(0)))
    return hits


def is_critical(text: str | None) -> bool:
    return bool(scan(text))


def check_and_alert(text: str | None, *, source_label: str = "document", alerter=None) -> list[NarrativeFlag]:
    """Scans the narrative and, if there are critical markers, sends an alert (the same forced
    display as critical numbers). `alerter(title, message)` — in production
    safety.alerts.send_critical_alert."""
    hits = scan(text)
    if hits and alerter is not None:
        cats = ", ".join(sorted({h.category for h in hits}))
        alerter("Health OS — critical narrative finding",
                f'In "{source_label}" markers [{cats}] were detected — needs a doctor\'s attention today.')
    return hits
