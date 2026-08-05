from typing import Any, Optional

from app.data.government_schemes import (
    GOVERNMENT_SCHEMES,
)


def get_scheme(
    scheme_id: str,
) -> Optional[dict[str, Any]]:

    return GOVERNMENT_SCHEMES.get(
        scheme_id.lower()
    )


def search_government_schemes(
    query: str,
) -> dict[str, Any]:
    """
    Search SahiSehat's verified government-scheme records.

    This does not ask Gemini to invent scheme information.
    """

    text = query.lower()

    matches = []

    for scheme in GOVERNMENT_SCHEMES.values():

        searchable_terms = [
            scheme["name"].lower(),
            scheme["short_name"].lower(),
            *[
                category.lower()
                for category in scheme["category"]
            ],
        ]

        # Direct scheme-name / abbreviation match.
        if any(
            term in text
            for term in searchable_terms
            if term
        ):
            matches.append(scheme)
            continue

        # Pregnancy/maternity queries can potentially
        # match both currently supported schemes.
        pregnancy_terms = [
            "pregnant",
            "pregnancy",
            "maternity",
            "mother",
            "delivery",
            "childbirth",
            "garbhavati",
            "pregnant woman",
        ]

        if (
            any(term in text for term in pregnancy_terms)
            and (
                "pregnancy" in scheme["category"]
                or "maternity" in scheme["category"]
            )
        ):
            matches.append(scheme)

    # Remove accidental duplicates.
    unique_matches = {
        scheme["id"]: scheme
        for scheme in matches
    }

    results = list(
        unique_matches.values()
    )

    return {
        "success": True,
        "count": len(results),
        "schemes": results,
    }