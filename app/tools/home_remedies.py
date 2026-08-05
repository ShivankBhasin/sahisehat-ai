from typing import Any
from typing import Optional

import httpx

from app.core.config import settings


class HomeRemedyServiceError(Exception):
    """Raised when the remedy service fails."""


async def search_home_remedies(
    query: str = "",
    ailment: Optional[str] = None,
    system: Optional[str] = None,
    page: int = 1,
    limit: int = 10,
) -> dict[str, Any]:

    url = (
        f"{settings.sahisehat_backend_url}"
        "/remedies"
    )

    params = {
        "page": page,
        "limit": limit,
    }

    if query:
        params["search"] = query

    if ailment:
        params["ailment"] = ailment

    if system:
        params["system"] = system

    try:

        async with httpx.AsyncClient(timeout=10.0) as client:

            response = await client.get(

                url,

                params=params,

            )

            response.raise_for_status()

    except httpx.TimeoutException as exc:

        raise HomeRemedyServiceError(
            "Home remedy service timed out."
        ) from exc

    except httpx.HTTPStatusError as exc:

        raise HomeRemedyServiceError(
            f"Home remedy service returned HTTP "
            f"{exc.response.status_code}."
        ) from exc

    except httpx.RequestError as exc:

        raise HomeRemedyServiceError(
            "Could not connect to home remedy service."
        ) from exc

    return response.json()