"""Text-to-speech utilities using edge-tts."""

import os
import tempfile

import edge_tts


async def generate_summary_audio(summary: str, output_path: str | None = None) -> str:
    """Convert summary text to an MP3 audio file using edge-tts.

    Args:
        summary: Summary text to convert to speech
        output_path: Optional path for the output MP3 file.
                      If None, a temporary file is created.

    Returns:
        Path to the generated MP3 audio file
    """
    voice = os.getenv("EDGE_TTS_VOICE", "en-US-AriaNeural")

    if output_path is None:
        fd, output_path = tempfile.mkstemp(suffix=".mp3", prefix="alpha_digest_")
        os.close(fd)

    communicate = edge_tts.Communicate(summary, voice)
    await communicate.save(output_path)
    return output_path
