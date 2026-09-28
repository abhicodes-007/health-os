"""A single escalation & silence policy + disclaimer (plan 4.3, Phase 1).

One canonical list of "when the system goes quiet and sends you to a doctor" + a versioned
list of red flags for the user's profile. Used both in summaries/reports and in the agent's
system prompt (so the rule lives in one place, not scattered across prompts).
"""
from __future__ import annotations

POLICY_VERSION = "2026-07-15"

DISCLAIMER = (
    "This is not medical care and does not replace a doctor. The system shows only what has "
    "been entered into it, and may contain recognition errors. For alarming symptoms — 103/112."
)

# Versioned list of red flags (plan 4.3). An update → change POLICY_VERSION + run evals.
RED_FLAGS = [
    "chest pain ± shortness of breath",
    "FAST signs of stroke (face asymmetry, arm weakness, speech impairment)",
    "\"worst headache of my life\"",
    "fever + neck stiffness ± rash",
    "acute scrotal pain (testicular torsion — window ~6 h, peak age 13–18)",
    "acute abdomen",
    "hemoptysis / melena / vomiting blood",
    "syncope (loss of consciousness)",
    "first-ever seizure",
    "asymmetric leg swelling + shortness of breath (DVT/PE)",
    "anaphylaxis",
    "sudden vision loss",
    "suicidal thoughts",
    "head trauma with loss of consciousness",
    "blast injury / concussion",
]

# When the system GOES QUIET with analytics and sends you to a doctor (single source of truth)
SILENCE_AND_ESCALATE = [
    "the critical-values rule-engine fired (a number outside a critical threshold)",
    "the critical-narrative-finding classifier fired (Bi-RADS 4-5, malign*, aneurysm, cito)",
    "the message contains any item from the RED_FLAGS list",
    "a symptom that is \"first-ever / worst in life / changed character\" — assessed de novo",
    "a question about drug interactions / whether X can be taken — refused until a DDI engine exists (plan 3.6)",
    "crisis / suicidal statements — fixed crisis protocol (7333, 103/112)",
]

# Forbidden phrasings (anti-automation-bias, plan 4.3)
FORBIDDEN_PHRASINGS = [
    "everything is normal / everything is under control (globally)",
    "I'm watching over your health",
    "you don't need to worry",
]


def escalation_policy_text() -> str:
    """Render the policy for the system prompt / documentation."""
    flags = "\n".join(f"  - {x}" for x in RED_FLAGS)
    esc = "\n".join(f"  - {x}" for x in SILENCE_AND_ESCALATE)
    return (
        f"# Escalation & silence policy (v{POLICY_VERSION})\n\n"
        f"{DISCLAIMER}\n\n"
        f"## The system goes quiet with analytics and sends you to a doctor if:\n{esc}\n\n"
        f"## Red flags (user's profile):\n{flags}\n\n"
        f"## Forbidden phrasings:\n"
        + "\n".join(f"  - {x}" for x in FORBIDDEN_PHRASINGS)
    )
