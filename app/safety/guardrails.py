import re
from dataclasses import dataclass
from typing import List

from app.models.schemas import RiskLevel


@dataclass
class SafetyAssessment:
    risk_level: RiskLevel
    emergency: bool
    requires_professional_care: bool
    matched_red_flags: List[str]


EMERGENCY_PATTERNS = {
    "severe_breathing_difficulty": [
        r"\b(can'?t|cannot|unable to)\s+breathe\b",
        r"\bsevere\s+(difficulty|trouble)\s+breathing\b",
        r"\bnot\s+breathing\b",
    ],

    "severe_chest_pain": [
        r"\bsevere\s+chest\s+pain\b",
        r"\bcrushing\s+chest\s+pain\b",
    ],

    "unconsciousness": [
        r"\bunconscious\b",
        r"\bnot\s+waking\s+up\b",
        r"\bunresponsive\b",
    ],

    "seizure": [
        r"\bseizure\b",
        r"\bconvulsion\b",
    ],

    "severe_bleeding": [
        r"\bheavy\s+bleeding\b",
        r"\bbleeding\s+(won'?t|will not)\s+stop\b",
        r"\bsevere\s+bleeding\b",
    ],

    "possible_stroke": [
        r"\bface\s+droop",
        r"\bslurred\s+speech\b",
        r"\bsudden\s+(weakness|numbness).*(one side|one-sided)\b",
    ],

    "self_harm": [
        r"\bkill\s+myself\b",
        r"\bend\s+my\s+life\b",
        r"\bwant\s+to\s+die\b",
        r"\bsuicide\b",
        r"\bhurt\s+myself\b",
    ],

    "pregnancy_emergency": [
        r"\bpregnan\w*.*heavy\s+bleeding\b",
        r"\bheavy\s+bleeding.*pregnan\w*\b",
        r"\bpregnan\w*.*severe\s+(stomach|abdominal|belly)\s+pain\b",
        r"\bsevere\s+(stomach|abdominal|belly)\s+pain.*pregnan\w*\b",
    ],
}


MODERATE_RISK_PATTERNS = [
    r"\bpersistent\s+fever\b",
    r"\bhigh\s+fever\b",
    r"\bdehydrated\b",
    r"\bdehydration\b",
    r"\brepeated\s+vomiting\b",
    r"\bvomiting\s+again\s+and\s+again\b",
    r"\bpregnan\w*\b",
]


def _matches_any(text: str, patterns: List[str]) -> bool:
    return any(
        re.search(pattern, text, flags=re.IGNORECASE)
        for pattern in patterns
    )


def assess_safety(message: str) -> SafetyAssessment:
    normalized = " ".join(message.strip().split())

    matched_red_flags: List[str] = []

    for flag_name, patterns in EMERGENCY_PATTERNS.items():
        if _matches_any(normalized, patterns):
            matched_red_flags.append(flag_name)

    if matched_red_flags:
        return SafetyAssessment(
            risk_level=RiskLevel.EMERGENCY,
            emergency=True,
            requires_professional_care=True,
            matched_red_flags=matched_red_flags,
        )

    if _matches_any(normalized, MODERATE_RISK_PATTERNS):
        return SafetyAssessment(
            risk_level=RiskLevel.MODERATE,
            emergency=False,
            requires_professional_care=True,
            matched_red_flags=[],
        )

    return SafetyAssessment(
        risk_level=RiskLevel.LOW,
        emergency=False,
        requires_professional_care=False,
        matched_red_flags=[],
    )