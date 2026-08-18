"""Text to speech, with graceful fallbacks.

The 2020 version hard-coded ``voices[2].id``, which raises ``IndexError`` on any
machine with fewer than three installed voices. Here the backend is chosen at
runtime, the voice is looked up by name, and if nothing is available the
assistant simply stops speaking instead of crashing.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ajeeb.config import Settings

log = logging.getLogger(__name__)

__all__ = ["Speaker", "SilentSpeaker", "Pyttsx3Speaker", "make_speaker", "to_mp3"]


@runtime_checkable
class Speaker(Protocol):
    """Anything that can say a sentence out loud."""

    name: str

    def say(self, text: str) -> None: ...

    def close(self) -> None: ...


class SilentSpeaker:
    """Used when no audio backend is available, or with ``--no-speak``."""

    name = "silent"

    def say(self, text: str) -> None:
        log.debug("silent speaker dropped: %s", text)

    def close(self) -> None:
        return None


class Pyttsx3Speaker:
    """Offline system voice (SAPI5 on Windows, NSSpeech on macOS, espeak on Linux)."""

    name = "pyttsx3"

    def __init__(self, rate: int = 165, voice_hint: str = "") -> None:
        import pyttsx3

        self._pyttsx3 = pyttsx3
        self._lock = threading.Lock()
        self._engine = self._build(rate, voice_hint)
        self._rate = rate
        self._voice_hint = voice_hint

    def _build(self, rate: int, voice_hint: str):
        engine = self._pyttsx3.init()
        engine.setProperty("rate", rate)
        if voice_hint:
            wanted = voice_hint.casefold()
            for voice in engine.getProperty("voices") or []:
                if wanted in (voice.name or "").casefold() or wanted in voice.id.casefold():
                    engine.setProperty("voice", voice.id)
                    break
            else:
                log.warning("no installed voice matches %r; using the default", voice_hint)
        return engine

    def say(self, text: str) -> None:
        if not text:
            return
        with self._lock:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except RuntimeError:
                # pyttsx3 can leave its run loop in a bad state; rebuild once.
                log.debug("pyttsx3 run loop wedged, rebuilding engine")
                self._engine = self._build(self._rate, self._voice_hint)
                self._engine.say(text)
                self._engine.runAndWait()

    def close(self) -> None:
        with self._lock:
            try:
                self._engine.stop()
            except Exception:  # pragma: no cover - teardown must never raise
                log.debug("pyttsx3 engine did not stop cleanly", exc_info=True)


def make_speaker(settings: Settings) -> Speaker:
    """Pick a speaker based on ``settings.tts_backend``, degrading to silence."""
    if not settings.speak_replies or settings.tts_backend == "silent":
        return SilentSpeaker()

    if settings.tts_backend in {"auto", "pyttsx3"}:
        try:
            return Pyttsx3Speaker(settings.speech_rate, settings.voice_hint)
        except Exception as exc:
            log.warning("offline speech unavailable (%s); continuing in text only", exc)
            if settings.tts_backend == "pyttsx3":
                return SilentSpeaker()

    if settings.tts_backend in {"auto", "gtts"}:
        log.info("gTTS produces audio files rather than live playback; use the web UI")

    return SilentSpeaker()


def to_mp3(text: str, *, language: str = "en") -> bytes | None:
    """Render ``text`` to MP3 bytes with gTTS, for browsers to play back.

    Returns ``None`` when gTTS is missing or offline, so callers can carry on
    showing the text.
    """
    if not text.strip():
        return None
    try:
        from io import BytesIO

        from gtts import gTTS
    except ImportError:
        log.debug("gTTS is not installed")
        return None

    try:
        buffer = BytesIO()
        gTTS(text=text, lang=language.split("-")[0].lower() or "en").write_to_fp(buffer)
        return buffer.getvalue()
    except Exception as exc:
        log.warning("speech synthesis failed: %s", exc)
        return None
