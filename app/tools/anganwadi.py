from typing import Any, Optional


# ============================================================
# VERIFIED COMMUNITY HEALTH SUPPORT INFORMATION
# ============================================================
#
# This is capability information only.
#
# It is NOT a directory of real Anganwadi centres,
# Anganwadi Workers, or ASHA workers.
#
# Sathi must never invent:
# - worker names
# - phone numbers
# - addresses
# - centre locations
# - live availability
# ============================================================


COMMUNITY_HEALTH_SUPPORT = {
    "anganwadi": {
        "type": "anganwadi",
        "name": "Anganwadi Worker",
        "short_name": "AWW",
        "description": (
            "Anganwadi Workers provide community-level support "
            "for women, mothers, and children through Anganwadi "
            "services."
        ),
        "can_help_with": [
            "pregnancy and maternal support",
            "child nutrition",
            "growth monitoring",
            "breastfeeding support",
            "early childhood care",
            "nutrition awareness",
            "government scheme guidance",
            "connecting families with appropriate local services",
        ],
    },

    "asha": {
        "type": "asha",
        "name": "ASHA Worker",
        "short_name": "ASHA",
        "description": (
            "ASHA workers act as a community-level link between "
            "people and the public healthcare system."
        ),
        "can_help_with": [
            "pregnancy support",
            "antenatal care guidance",
            "institutional delivery support",
            "maternal and newborn health",
            "immunisation guidance",
            "community health awareness",
            "government health programme guidance",
            "connecting people with appropriate health facilities",
        ],
    },
}


def infer_community_worker(
    message: str,
) -> Optional[str]:
    """
    Determine whether the user is specifically asking about
    an Anganwadi Worker or an ASHA Worker.
    """

    text = message.lower().strip()

    anganwadi_terms = [
        "anganwadi",
        "anganwaadi",
        "anganwadi worker",
        "anganwaadi worker",
        "anganwadi didi",
        "anganwaadi didi",
        "anganwadi centre",
        "anganwadi center",
        "anganwaadi centre",
        "anganwaadi center",
        "aww",
    ]

    asha_terms = [
        "asha",
        "asha worker",
        "asha didi",
        "accredited social health activist",
    ]

    if any(
        term in text
        for term in anganwadi_terms
    ):
        return "anganwadi"

    if any(
        term in text
        for term in asha_terms
    ):
        return "asha"

    return None


def get_community_health_support(
    worker_type: Optional[str] = None,
) -> dict[str, Any]:
    """
    Return SahiSehat's community-health support information.

    If a worker type is specified, return information only
    about that worker type.

    Otherwise return both Anganwadi and ASHA information.
    """

    if worker_type:

        worker = COMMUNITY_HEALTH_SUPPORT.get(
            worker_type
        )

        if worker:

            return {
                "success": True,
                "count": 1,
                "workers": [worker],
            }

        return {
            "success": False,
            "count": 0,
            "workers": [],
        }

    workers = list(
        COMMUNITY_HEALTH_SUPPORT.values()
    )

    return {
        "success": True,
        "count": len(workers),
        "workers": workers,
    }