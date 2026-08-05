from typing import Any, Optional

import httpx

from app.core.config import settings


class FacilityServiceError(Exception):
    """Raised when the SahiSehat facility service cannot be reached or fails."""


def normalize_facility_type(facility_type: str) -> Optional[str]:
    """
    Convert the facility type understood by Sathi into the exact
    type expected by the SahiSehat backend.
    """

    normalized = facility_type.strip().lower()

    mappings = {
        "phc": "PHC",
        "bphc": "PHC",
        "primary health centre": "PHC",
        "primary health center": "PHC",

        "hospital": "Hospital",
        "hospitals": "Hospital",
    }

    return mappings.get(normalized)


async def search_facilities(
    facility_type: str,
    page: int = 1,
    limit: int = 5,
    state: Optional[str] = None,
    district: Optional[str] = None,
    city: Optional[str] = None,
) -> dict[str, Any]:

    backend_type = normalize_facility_type(facility_type)

    if backend_type is None:
        return {
            "success": False,
            "error": "unsupported_facility_type",
            "message": (
                "The facility database currently supports "
                "PHCs/BPHCs and hospitals."
            ),
            "facilities": [],
        }

    params: dict[str, Any] = {
        "type": backend_type,
        "page": page,
        "limit": limit,
    }

    if state:
        params["state"] = state

    if district:
        params["district"] = district

    if city:
        params["city"] = city

    url = f"{settings.sahisehat_backend_url}/facilities"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                params=params,
            )

            response.raise_for_status()

    except httpx.TimeoutException as exc:
        raise FacilityServiceError(
            "The facility service timed out."
        ) from exc

    except httpx.HTTPStatusError as exc:
        raise FacilityServiceError(
            f"Facility service returned HTTP "
            f"{exc.response.status_code}."
        ) from exc

    except httpx.RequestError as exc:
        raise FacilityServiceError(
            "Could not connect to the facility service."
        ) from exc

    data = response.json()

    raw_facilities = data.get(
        "facilities",
        []
    )

    facilities = []

    for facility in raw_facilities:

        location = facility.get("location") or {}
        coordinates = location.get("coordinates") or []

        longitude = (
            coordinates[0]
            if len(coordinates) >= 2
            else None
        )

        latitude = (
            coordinates[1]
            if len(coordinates) >= 2
            else None
        )

        facilities.append(
            {
                "id": facility.get("_id"),
                "name": facility.get("name"),
                "type": facility.get("type"),
                "address": facility.get("address"),
                "city": facility.get("city"),
                "district": facility.get("district"),
                "state": facility.get("state"),
                "ownership": facility.get("ownership"),
                "services": facility.get("services", []),
                "latitude": latitude,
                "longitude": longitude,
            }
        )

    return {
        "success": True,
        "count": len(facilities),
        "total": data.get("total"),
        "page": data.get("page"),
        "total_pages": data.get("totalPages"),
        "facilities": facilities,
    }