from __future__ import annotations

import base64
import wave
from pathlib import Path
from uuid import uuid4

from google import genai
from google.genai import types

from app.core.config import settings

# ============================================================
# GEMINI TTS SERVICE
# ============================================================

client = genai.Client(
    api_key=settings.gemini_api_key,
)

# Folder where generated audio will be stored
OUTPUT_DIR = Path("generated_audio")
OUTPUT_DIR.mkdir(exist_ok=True)

# Good default voice
VOICE_NAME = "Kore"

TTS_MODEL = "gemini-3.1-flash-tts-preview"


async def text_to_speech(
    text: str,
) -> str:
    """
    Generate speech from Sathi's response.

    Returns:
        Relative path of generated WAV file.
    """

    response = await client.aio.models.generate_content(
        model=TTS_MODEL,
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=VOICE_NAME,
                    )
                )
            ),
        ),
    )

    pcm_data = None

    for part in response.candidates[0].content.parts:
        if (
            hasattr(part, "inline_data")
            and part.inline_data
            and part.inline_data.data
        ):
            pcm_data = base64.b64decode(
                part.inline_data.data
            )
            print(type(part.inline_data.data))
            print(len(part.inline_data.data))
            print(part.inline_data.mime_type)
            pcm_data = part.inline_data.data
            print("PCM length:", len(pcm_data))
            break

    if pcm_data is None:
        raise RuntimeError(
            "Gemini returned no audio."
        )

    filename = f"{uuid4()}.wav"

    output_path = OUTPUT_DIR / filename

    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(pcm_data)

    return str(output_path)