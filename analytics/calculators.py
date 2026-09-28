"""Risk calculators with a HARD age gate (plan 5, level 1).

SCORE2 is validated for 40–69, ASCVD 40–79, FRAX 40–90. For younger ages the system
REFUSES to compute and explains why: the 10-year risk in the young is always "low" even
with a terrible profile — a known false reassurance. Instead — monitoring the trajectory of
factors and a lifetime approach (LIFE-CVD) where applicable.

This is the gate itself (the most important part), not the coefficient implementation (added
from a validated source, in Phase 5 in full). BMI — no age gate, plain arithmetic.
"""
from __future__ import annotations

from dataclasses import dataclass

_GATES = {
    "SCORE2": (40, 69),
    "ASCVD": (40, 79),
    "FRAX": (40, 90),
}


@dataclass
class CalculatorGate:
    name: str
    applicable: bool
    message: str


def calculator_applicable(name: str, age: int) -> CalculatorGate:
    if name not in _GATES:
        return CalculatorGate(name, False, f"Unknown calculator {name}.")
    lo, hi = _GATES[name]
    if lo <= age <= hi:
        return CalculatorGate(name, True, f"{name} is applicable for age {age} ({lo}–{hi}).")
    if age < lo:
        return CalculatorGate(
            name, False,
            f"{name} is NOT computed for age {age} (validated {lo}–{hi}). In the young the 10-year "
            f"risk is always 'low' even with a bad profile — false reassurance. Instead: "
            f"monitor the trajectory of factors (LDL, BP, smoking, family history) + lifetime risk.")
    return CalculatorGate(name, False,
                          f"{name} is NOT computed for age {age} (validated {lo}–{hi}).")


def bmi(weight_kg: float, height_cm: float) -> dict:
    """BMI — no age gate (for adults). Returns the value + WHO category."""
    if height_cm <= 0:
        return {"error": "invalid height"}
    h = height_cm / 100.0
    value = weight_kg / (h * h)
    if value < 18.5:
        cat = "underweight"
    elif value < 25:
        cat = "normal"
    elif value < 30:
        cat = "overweight"
    else:
        cat = "obese"
    return {"bmi": round(value, 1), "category": cat}
