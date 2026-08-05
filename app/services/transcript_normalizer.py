from __future__ import annotations

from google import genai

from app.core.config import settings

client = genai.Client(
    api_key=settings.gemini_api_key,
)


async def normalize_transcript(
    transcript: str,
) -> str:
    """
    Normalize Whisper transcripts before sending them
    to Sathi.

    Rules:

    - Preserve the meaning exactly.
    - Do NOT answer the user.
    - Do NOT summarize.
    - Only clean the transcript.

    Special handling:

    • If Hindi is written in Urdu script,
      convert it to standard Hindi (Devanagari).

    • Preserve English.

    • Preserve Hinglish naturally.

    • Correct obvious transcription mistakes.

    • Never invent information.
    """

    prompt = f"""
You are a transcript normalizer.

You NEVER answer the user's question.

You ONLY clean speech-to-text output.

Rules:

1. Preserve meaning exactly.

2. If the speaker spoke Hindi
   but the transcript is in Urdu script,
   convert it into standard Hindi
   using Devanagari.

3. Preserve Hinglish naturally.

4. Preserve English.

5. Fix obvious speech-recognition errors.

6. Return ONLY the corrected transcript.

Transcript:

{transcript}
"""

    response = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
    )

    return response.text.strip()