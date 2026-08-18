"""Speech to text.

Two entry points, both built on SpeechRecognition:

* :func:`listen` grabs a phrase from a live microphone (terminal front-end).
* :func:`transcribe` turns recorded audio bytes into text (browser front-end,
  where the microphone belongs to the browser and PyAudio is not needed).

Every failure comes back as a :class:`Transcript` with a human-readable reason
rather than the original code's bare ``except`` that hid real bugs.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ajeeb.config import Settings

log = logging.getLogger(__name__)

__all__ = ["Transcript", "MicrophoneUnavailable", "listen", "transcribe", "microphone_ready"]


class MicrophoneUnavailable(RuntimeError):
    """No usable microphone or the audio stack is missing."""


@dataclass(frozen=True, slots=True)
class Transcript:
    text: str = ""
    error: str | None = None

    def __bool__(self) -> bool:
        return bool(self.text)


def _recognizer(settings: Settings):
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 0.8
    recognizer.dynamic_energy_threshold = True
    return sr, recognizer


def microphone_ready() -> bool:
    """True when SpeechRecognition and a working input device are both present."""
    try:
        import speech_recognition as sr

        return bool(sr.Microphone.list_microphone_names())
    except Exception:
        return False


def listen(settings: Settings, *, on_listening=None) -> Transcript:
    """Record one phrase from the default microphone and transcribe it."""
    try:
        sr, recognizer = _recognizer(settings)
    except ImportError as exc:
        raise MicrophoneUnavailable(
            "SpeechRecognition is not installed. Run: pip install -e .[cli]"
        ) from exc

    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.4)
            if on_listening:
                on_listening()
            audio = recognizer.listen(
                source,
                timeout=settings.listen_timeout,
                phrase_time_limit=settings.phrase_time_limit,
            )
    except AttributeError as exc:  # PyAudio missing -> sr.Microphone has no backend
        raise MicrophoneUnavailable(
            "No audio backend found. Install PyAudio, or use the web UI."
        ) from exc
    except OSError as exc:
        raise MicrophoneUnavailable(f"Microphone unavailable: {exc}") from exc
    except Exception as exc:
        if exc.__class__.__name__ == "WaitTimeoutError":
            return Transcript(error="I did not hear anything.")
        raise

    return _recognize(audio, recognizer, settings)


def transcribe(audio_bytes: bytes, settings: Settings) -> Transcript:
    """Transcribe a recorded WAV/AIFF/FLAC clip, e.g. from ``st.audio_input``."""
    if not audio_bytes:
        return Transcript(error="The recording was empty.")
    try:
        sr, recognizer = _recognizer(settings)
    except ImportError as exc:
        return Transcript(error=f"SpeechRecognition is not installed ({exc}).")

    try:
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio = recognizer.record(source)
    except Exception as exc:
        log.debug("could not decode recording: %s", exc)
        return Transcript(error="I could not read that recording.")

    return _recognize(audio, recognizer, settings)


def _recognize(audio, recognizer, settings: Settings) -> Transcript:
    import speech_recognition as sr

    try:
        text = recognizer.recognize_google(audio, language=settings.language)
    except sr.UnknownValueError:
        return Transcript(error="I could not make out the words. Say that again?")
    except sr.RequestError as exc:
        return Transcript(error=f"The speech service is unreachable ({exc}).")
    return Transcript(text=text.strip())
