from typing import Any

import httpx

from app.core.config import settings


class AmbulanceServiceError(Exception):
    """Raised when the ambulance service cannot be reached."""


async def get_nearby_ambulances() -> dict[str, Any]:

    url = f"{settings.sahisehat_backend_url}/ambulances"

    try:

        async with httpx.AsyncClient(timeout=10.0) as client:

            response = await client.get(url)

            response.raise_for_status()

    except httpx.TimeoutException as exc:

        raise AmbulanceServiceError(
            "The ambulance service timed out."
        ) from exc

    except httpx.HTTPStatusError as exc:

        raise AmbulanceServiceError(
            f"Ambulance service returned HTTP "
            f"{exc.response.status_code}."
        ) from exc

    except httpx.RequestError as exc:

        raise AmbulanceServiceError(
            "Could not connect to the ambulance service."
        ) from exc

    data = response.json()

    return {

        "success": True,

        "count": len(data.get("ambulances", [])),

        "ambulances": data.get("ambulances", [])

    }