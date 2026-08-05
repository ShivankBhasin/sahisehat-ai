from __future__ import annotations

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from app.services.speech import transcribe_audio
from app.core.config import settings
from app.llm.orchestrator import process_chat
from app.models.schemas import ChatRequest
from app.services.transcript_normalizer import normalize_transcript
from app.services.tts import text_to_speech


router = APIRouter(
    prefix="/api/voice",
    tags=["voice"],
)

# ============================================================
# CONFIGURATION
# ============================================================

MAX_AUDIO_SIZE = 15 * 1024 * 1024  # 15 MB


# ============================================================
# VOICE CHAT ENDPOINT
# ============================================================

@router.post("/chat")
async def voice_chat(
    audio: UploadFile = File(...),
    session_id: str | None = Form(default=None),
):
    """
    Voice entry point for Sathi.

    FLOW:

    User audio
        ↓
    Speech-to-text
        ↓
    Existing Sathi process_chat()
        ↓
    Same safety + tools + conversation logic
        ↓
    Text response

    Text-to-speech will be added after this pipeline
    has been verified.
    """

    try:

        # ----------------------------------------------------
        # READ AUDIO
        # ----------------------------------------------------

        audio_bytes = await audio.read()

        if not audio_bytes:
            raise HTTPException(
                status_code=400,
                detail="The uploaded audio file is empty.",
            )

        if len(audio_bytes) > MAX_AUDIO_SIZE:
            raise HTTPException(
                status_code=413,
                detail=(
                    "Audio file is too large. "
                    "Maximum allowed size is 15 MB."
                ),
            )

        # ----------------------------------------------------
        # SPEECH → TEXT
        # ----------------------------------------------------

        transcription = await transcribe_audio(
            audio_bytes=audio_bytes,
            filename=audio.filename,
            )

        transcription = await normalize_transcript(
            transcription
            )

        print(
            f"Sathi voice transcription: {transcription}"
        )

        # ----------------------------------------------------
        # TEXT → EXISTING SATHI
        # ----------------------------------------------------

        chat_request = ChatRequest(
            message=transcription,
            session_id=session_id,
        )

        chat_response = await process_chat(
            chat_request
        )
        audio_path = await text_to_speech(
            chat_response.response
        )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return {
            "success": True,

            "transcription": transcription,

            "session_id": (
                chat_response.session_id
            ),

            "response": (
                chat_response.response
            ),

            "detected_language": (
                chat_response.detected_language
            ),

            "intent": (
                chat_response.intent
            ),

            "risk_level": (
                chat_response.risk_level
            ),

            "requires_professional_care": (
                chat_response.requires_professional_care
            ),

            "emergency": (
                chat_response.emergency
            ),

            # Text-to-speech comes next.
            "audio_response": audio_path,
        }

    except HTTPException:
        raise

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:

        print(
            f"SahiSehat voice error: {exc}"
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Sathi could not process the voice request."
            ),
        )

    finally:
        await audio.close()