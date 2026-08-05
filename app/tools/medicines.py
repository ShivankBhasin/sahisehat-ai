from typing import Any

import httpx

from app.core.config import settings


class MedicineServiceError(Exception):
    """Raised when medicine search fails."""


async def search_medicines(
    query: str,
    page: int = 1,
    limit: int = 10,
) -> dict[str, Any]:

    url = (
        f"{settings.sahisehat_backend_url}"
        "/medicines"
    )

    try:

        async with httpx.AsyncClient(timeout=10.0) as client:

            response = await client.get(

                url,

                params={
                    "search": query,
                    "page": page,
                    "limit": limit,
                }

            )

            response.raise_for_status()

    except httpx.TimeoutException as exc:

        raise MedicineServiceError(
            "Medicine service timed out."
        ) from exc

    except httpx.HTTPStatusError as exc:

        raise MedicineServiceError(
            f"Medicine service returned HTTP "
            f"{exc.response.status_code}."
        ) from exc

    except httpx.RequestError as exc:

        raise MedicineServiceError(
            "Could not connect to medicine service."
        ) from exc

    return response.json()