from __future__ import annotations

import os
import tempfile

import whisper

# ============================================================
# SAHISEHAT SPEECH TO TEXT SERVICE
# ============================================================


MODEL_NAME = "tiny"

print(f"Loading Whisper model: {MODEL_NAME}")

model = whisper.load_model(MODEL_NAME)

print("Whisper loaded successfully.")


SUPPORTED_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".ogg",
    ".webm",
}


async def transcribe_audio(
    audio_bytes: bytes,
    filename: str,
) -> str:
    """
    Convert speech into text.

    Whisper automatically detects:
    - English
    - Hindi
    - Hinglish
    - Many Indian languages
    """

    if not audio_bytes:
        raise ValueError(
            "Uploaded audio is empty."
        )

    extension = os.path.splitext(filename)[1].lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported audio format: {extension}"
        )

    temp_file = None

    try:

        with tempfile.NamedTemporaryFile(
            suffix=extension,
            delete=False,
        ) as f:

            f.write(audio_bytes)

            temp_file = f.name

        result = model.transcribe(
            temp_file,
            fp16=False,
            language = "hi",
        )

        text = result["text"].strip()
        print("\n" + "=" * 60)
        print("WHISPER RAW RESULT")
        print(f"Detected language: {result.get('language')}")
        print(f"Transcript: {result['text']}")
        print("=" * 60 + "\n")

        if not text:
            raise ValueError(
                "No speech detected."
            )

        return text

    finally:

        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)