"""Crisis protocol (plan 4.6) — deterministic, independent of the LLM/API.

A Telegram bot at 3am is de facto the first line. This can't be left to the LLM's mood.
A local keyword/regex layer (zero dependencies) is the first net; an LLM classifier (Phase 4)
sits on top. The fixed response with 7333/103/112 must be delivered even with a dead API.

Suicidality is NOT an observation: it doesn't go into trends/correlations/reports (handled
separately).
"""
from __future__ import annotations

import re
import unicodedata

# High-recall patterns (a false positive is better than a miss). uk/ru/en.
_PATTERNS = [
    r"не хоч(?:у|еться).{0,20}жити", r"немає сенсу жити", r"не бачу сенсу",
    r"хочу померти", r"краще б я помер", r"краще не прокидатись",
    r"покінчити з (собою|життям)", r"накласти на себе руки", r"звести рахунки з життям",
    r"порізати себе", r"завдати собі шкоди", r"зробити собі боляче",
    r"суїцид", r"суицид", r"самогубств",
    r"не хочу больше жить", r"хочу умереть", r"покончить с собой", r"свести счёты",
    r"kill myself", r"want to die", r"end my life", r"suicid", r"self[- ]?harm",
    r"no reason to live", r"better off dead",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PATTERNS]


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text.replace("ё", "е")).lower()


def is_crisis(text: str | None) -> bool:
    if not text:
        return False
    n = _norm(text)
    return any(rx.search(n) for rx in _COMPILED)


def crisis_response(emergency_contact: str | None = None) -> str:
    """Fixed crisis response. No analytics, no "let's look at your trends"."""
    lines = [
        "It sounds like things are very hard for you right now. You're not alone — there are "
        "people ready to listen right now.",
        "",
        "📞 **Lifeline Ukraine — 7333** (free, 24/7, confidential)",
        "🚨 **Emergency services — 103 or 112**",
    ]
    if emergency_contact:
        lines.append(f"👤 Your trusted contact: {emergency_contact}")
    lines += [
        "",
        "If there is an immediate threat to life — please call 103/112 right now.",
        "I'm not a medical professional and I don't replace crisis care, but I'm here and I "
        "won't leave you.",
    ]
    return "\n".join(lines)
