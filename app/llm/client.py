import asyncio
import random
from typing import Optional

from google import genai
from google.genai import types

from app.core.config import settings
from app.llm.prompts import SAHISEHAT_SYSTEM_PROMPT
from app.models.schemas import ChatMessage


class GeminiServiceError(Exception):
    """Raised when all configured Gemini attempts fail."""


class GeminiClient:
    def __init__(self):
        self.client = genai.Client(
            api_key=settings.gemini_api_key
        )

        # Primary model comes from .env
        self.primary_model = settings.gemini_model

        # Fallbacks are models already confirmed as visible
        # to this Gemini API key.
        self.fallback_models = [
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
        ]

        # Number of attempts PER model.
        self.max_attempts_per_model = 3

    def _build_conversation(
        self,
        message: str,
        history: list[ChatMessage],
    ) -> str:

        conversation_parts = []

        for item in history:
            role_label = (
                "USER"
                if item.role == "user"
                else "SATHI"
            )

            conversation_parts.append(
                f"{role_label}: {item.content}"
            )

        conversation_parts.append(
            f"USER: {message}"
        )

        return "\n\n".join(
            conversation_parts
        )

    def _get_status_code(
        self,
        exc: Exception,
    ) -> Optional[int]:

        # google-genai API errors generally expose a code,
        # but we keep this defensive in case the SDK changes.
        code = getattr(exc, "code", None)

        if isinstance(code, int):
            return code

        status_code = getattr(
            exc,
            "status_code",
            None,
        )

        if isinstance(status_code, int):
            return status_code

        # Last-resort parsing for SDK exception formats.
        error_text = str(exc)

        for candidate in (
            429,
            500,
            502,
            503,
            504,
        ):
            if str(candidate) in error_text:
                return candidate

        return None

    def _is_retryable_error(
        self,
        exc: Exception,
    ) -> bool:

        status_code = self._get_status_code(
            exc
        )

        return status_code in {
            429,  # Rate limited
            500,  # Temporary server failure
            502,  # Bad gateway
            503,  # Service unavailable / high demand
            504,  # Gateway timeout
        }

    async def _wait_before_retry(
        self,
        attempt: int,
    ) -> None:

        # Exponential backoff:
        #
        # attempt 1 -> roughly 1 sec
        # attempt 2 -> roughly 2 sec
        # attempt 3 -> roughly 4 sec
        #
        # Jitter prevents multiple clients retrying at
        # exactly the same instant.

        base_delay = 2 ** (attempt - 1)
        jitter = random.uniform(0.0, 0.5)

        delay = base_delay + jitter

        print(
            f"Gemini retry waiting "
            f"{delay:.2f} seconds..."
        )

        await asyncio.sleep(delay)

    async def _call_model(
        self,
        model: str,
        conversation_text: str,
    ) -> str:

        response = await self.client.aio.models.generate_content(
            model=model,
            contents=conversation_text,
            config=types.GenerateContentConfig(
                system_instruction=SAHISEHAT_SYSTEM_PROMPT,
                temperature=0.3,
                top_p=0.9,
                max_output_tokens=1200,
            ),
        )

        if not response.text:
            raise RuntimeError(
                f"{model} returned an empty response."
            )

        return response.text.strip()

    async def generate_response(
        self,
        message: str,
        history: list[ChatMessage],
    ) -> str:

        conversation_text = self._build_conversation(
            message=message,
            history=history,
        )

        models = [
            self.primary_model,
            *self.fallback_models,
        ]

        # Remove accidental duplicates while keeping order.
        models = list(dict.fromkeys(models))

        last_error: Optional[Exception] = None

        for model_index, model in enumerate(models):

            print(
                f"Gemini: trying model {model}"
            )

            for attempt in range(
                1,
                self.max_attempts_per_model + 1,
            ):

                try:
                    response = await self._call_model(
                        model=model,
                        conversation_text=conversation_text,
                    )

                    if model != self.primary_model:
                        print(
                            f"Gemini fallback succeeded: "
                            f"{model}"
                        )

                    return response

                except Exception as exc:
                    last_error = exc

                    retryable = self._is_retryable_error(
                        exc
                    )

                    print(
                        f"Gemini model={model}, "
                        f"attempt={attempt}/"
                        f"{self.max_attempts_per_model}, "
                        f"retryable={retryable}, "
                        f"error={exc}"
                    )

                    # Invalid key, invalid request, unavailable
                    # model, etc. should not be repeatedly retried.
                    if not retryable:
                        break

                    # Retry the same model if attempts remain.
                    if (
                        attempt
                        < self.max_attempts_per_model
                    ):
                        await self._wait_before_retry(
                            attempt
                        )

            # If this was not the last model, move to fallback.
            if model_index < len(models) - 1:
                print(
                    f"Gemini: switching from {model} "
                    f"to fallback model..."
                )

        raise GeminiServiceError(
            "All configured Gemini models failed. "
            f"Last error: {last_error}"
        )


gemini_client = GeminiClient()