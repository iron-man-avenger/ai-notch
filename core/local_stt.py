"""
Local On-Device Speech-to-Text Fallback Engine powered by Cactus Compute's Whistle (needle).
Provides offline, ultrafast (<50ms TTFT) on-device transcription for English voice commands
with zero external network dependencies.
"""

import os
import io
import tempfile
from typing import Optional

os.environ["NEEDLE_TELEMETRY"] = "0"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

_NEEDLE_AVAILABLE = None

def is_whistle_available() -> bool:
    global _NEEDLE_AVAILABLE
    if _NEEDLE_AVAILABLE is not None:
        return _NEEDLE_AVAILABLE
    try:
        import needle
        _NEEDLE_AVAILABLE = True
    except Exception:
        _NEEDLE_AVAILABLE = False
    return _NEEDLE_AVAILABLE

def transcribe_with_cactus_whistle(audio_bytes: bytes, filename: str = "voice.wav") -> Optional[str]:
    """
    Transcribes audio using Cactus Compute Whistle (cactus-needle).
    Runs 100% locally on CPU in ~45ms without network calls.
    Returns cleaned English text or None.
    """
    if not is_whistle_available():
        return None

    if not audio_bytes or len(audio_bytes) < 400:
        return None

    temp_path = None
    try:
        import needle

        # If audio_bytes is already a WAV file, write to a temp file
        ext = os.path.splitext(filename)[1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(audio_bytes)
            temp_path = tmp.name

        # Call needle on-device transcribe
        res = needle.transcribe(temp_path, language="en")
        if res and isinstance(res, dict):
            text = (res.get("text") or "").strip()
            # Filter silence / empty noise
            noise_hallucinations = {"thank you.", "thank you", "thanks for watching", "subtitles by", "bye.", ".", ""}
            if text and text.lower() not in noise_hallucinations:
                print(f"[Cactus Whistle Local STT] ({res.get('ttft_ms', 0):.1f}ms) Transcribed: \"{text}\"")
                return text
    except Exception as e:
        print(f"[Cactus Whistle Fallback Warning] {e}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

    return None
