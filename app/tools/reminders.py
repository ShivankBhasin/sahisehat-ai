from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4


# ============================================================
# SAHISEHAT REMINDER TOOL
# ============================================================
#
# Current responsibility:
#
# - Understand reminder requests
# - Extract basic schedule information
# - Create a structured reminder object
# - Keep reminders temporarily in memory during development
#
# Current limitations:
#
# - Does NOT send notifications
# - Does NOT send SMS / WhatsApp / push notifications
# - Does NOT persist after the AI server restarts
# - Does NOT claim a reminder has been delivered
#
# Later this can be connected to the backend / n8n notification
# workflow without changing Sathi's conversational interface.
# ============================================================


@dataclass
class Reminder:
    id: str
    session_id: str
    reminder_type: str
    title: str
    original_message: str
    time_text: Optional[str]
    frequency: Optional[str]
    status: str
    created_at: str


# Temporary development storage.
#
# IMPORTANT:
# These reminders disappear when the server restarts.
_REMINDERS: dict[str, Reminder] = {}


# ============================================================
# REMINDER TYPE DETECTION
# ============================================================


def infer_reminder_type(
    message: str,
) -> str:

    text = message.lower()

    medication_terms = [
        "medicine",
        "medication",
        "tablet",
        "capsule",
        "pill",
        "dose",
        "dawai",
        "dawa",
    ]

    pregnancy_terms = [
        "pregnancy",
        "pregnant",
        "antenatal",
        "prenatal",
        "checkup",
        "check-up",
        "doctor appointment",
    ]

    if any(
        term in text
        for term in medication_terms
    ):
        return "medication"

    if any(
        term in text
        for term in pregnancy_terms
    ):
        return "pregnancy_care"

    return "general"


# ============================================================
# TIME EXTRACTION
# ============================================================


def extract_time_text(
    message: str,
) -> Optional[str]:

    text = message.lower()

    patterns = [
        # 8 PM / 8:30 PM / 8pm
        r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",

        # at 8 / at 8:30
        r"\bat\s+\d{1,2}(?::\d{2})?\b",

        # morning / afternoon / evening / night
        r"\b(?:morning|afternoon|evening|night)\b",

        # Hindi/Hinglish common forms
        r"\bsubah\b",
        r"\bdopahar\b",
        r"\bshaam\b",
        r"\braat\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(0).strip()

    return None


# ============================================================
# FREQUENCY EXTRACTION
# ============================================================


def extract_frequency(
    message: str,
) -> Optional[str]:

    text = message.lower()

    frequency_patterns = [
        (
            "daily",
            [
                "every day",
                "everyday",
                "daily",
                "roz",
                "har din",
            ],
        ),
        (
            "weekly",
            [
                "every week",
                "weekly",
                "har hafte",
                "har hafta",
            ],
        ),
        (
            "twice_daily",
            [
                "twice a day",
                "two times a day",
                "twice daily",
                "din mein do baar",
            ],
        ),
        (
            "three_times_daily",
            [
                "three times a day",
                "three times daily",
                "din mein teen baar",
            ],
        ),
    ]

    for frequency, phrases in frequency_patterns:

        if any(
            phrase in text
            for phrase in phrases
        ):
            return frequency

    return None


# ============================================================
# TITLE CREATION
# ============================================================


def create_reminder_title(
    reminder_type: str,
) -> str:

    titles = {
        "medication": "Medication Reminder",
        "pregnancy_care": "Pregnancy Care Reminder",
        "general": "Health Reminder",
    }

    return titles.get(
        reminder_type,
        "Health Reminder",
    )


# ============================================================
# CREATE REMINDER
# ============================================================


def create_reminder(
    session_id: str,
    message: str,
) -> dict[str, Any]:

    reminder_type = infer_reminder_type(
        message
    )

    time_text = extract_time_text(
        message
    )

    frequency = extract_frequency(
        message
    )

    reminder_id = str(
        uuid4()
    )

    reminder = Reminder(
        id=reminder_id,
        session_id=session_id,
        reminder_type=reminder_type,
        title=create_reminder_title(
            reminder_type
        ),
        original_message=message,
        time_text=time_text,
        frequency=frequency,
        status="draft",
        created_at=datetime.utcnow().isoformat(),
    )

    _REMINDERS[reminder_id] = reminder

    missing_fields = []

    if not time_text:
        missing_fields.append(
            "time"
        )

    return {
        "success": True,
        "reminder": asdict(reminder),
        "missing_fields": missing_fields,
        "ready_for_scheduling": (
            len(missing_fields) == 0
        ),
        "delivery_connected": False,
    }


# ============================================================
# GET REMINDER
# ============================================================


def get_reminder(
    reminder_id: str,
) -> Optional[dict[str, Any]]:

    reminder = _REMINDERS.get(
        reminder_id
    )

    if not reminder:
        return None

    return asdict(reminder)


# ============================================================
# LIST SESSION REMINDERS
# ============================================================


def get_session_reminders(
    session_id: str,
) -> list[dict[str, Any]]:

    reminders = [
        asdict(reminder)
        for reminder in _REMINDERS.values()
        if reminder.session_id == session_id
    ]

    return reminders