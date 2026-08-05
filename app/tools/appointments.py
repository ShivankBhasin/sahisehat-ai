from typing import Any

import httpx

from app.core.config import settings


class AppointmentServiceError(Exception):
    """Raised when appointment service fails."""


async def get_appointments(
    token: str,
) -> dict[str, Any]:

    url = (
        f"{settings.sahisehat_backend_url}"
        "/appointments"
    )

    try:

        async with httpx.AsyncClient(timeout=10.0) as client:

            response = await client.get(

                url,

                headers={

                    "Authorization":
                    f"Bearer {token}"

                }

            )

            response.raise_for_status()

    except httpx.TimeoutException as exc:

        raise AppointmentServiceError(
            "Appointment service timed out."
        ) from exc

    except httpx.HTTPStatusError as exc:

        raise AppointmentServiceError(
            f"Appointment service returned HTTP "
            f"{exc.response.status_code}."
        ) from exc

    except httpx.RequestError as exc:

        raise AppointmentServiceError(
            "Could not connect to appointment service."
        ) from exc

    return response.json()


async def create_appointment(
    payload: dict[str, Any],
    token: str,
) -> dict[str, Any]:

    url = (
        f"{settings.sahisehat_backend_url}"
        "/appointments"
    )

    try:

        async with httpx.AsyncClient(timeout=10.0) as client:

            response = await client.post(

                url,

                headers={

                    "Authorization":
                    f"Bearer {token}"

                },

                json=payload,

            )

            response.raise_for_status()

    except httpx.TimeoutException as exc:

        raise AppointmentServiceError(
            "Appointment service timed out."
        ) from exc

    except httpx.HTTPStatusError as exc:

        raise AppointmentServiceError(
            f"Appointment service returned HTTP "
            f"{exc.response.status_code}."
        ) from exc

    except httpx.RequestError as exc:

        raise AppointmentServiceError(
            "Could not connect to appointment service."
        ) from exc

    return response.json()