from fastapi import APIRouter, HTTPException
from app.llm.client import GeminiServiceError

from app.llm.orchestrator import process_chat
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
)
from app.services.conversation import conversation_store


router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"],
)


@router.post(
    "",
    response_model=ChatResponse,
)
async def chat(
    request: ChatRequest,
) -> ChatResponse:

    try:
        return await process_chat(request)

    except GeminiServiceError as exc:
        print(
            f"Gemini service unavailable: {exc}"
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "Sathi is temporarily unable to reach "
                "the AI service. Please try again shortly."
            ),
        )

    except Exception as exc:
        print(
            f"SahiSehat chat error: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "SahiSehat AI could not process "
                "the request."
            ),
        )


@router.delete(
    "/{session_id}",
)
async def clear_conversation(
    session_id: str,
):
    conversation_store.clear(
        session_id
    )

    return {
        "success": True,
        "message": "Conversation cleared.",
    }