"""Runtime configuration for Mr. Ajeeb.

Every value can be overridden with an ``AJEEB_*`` environment variable, so the
same code runs in a terminal, in Streamlit, or in CI without edits.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

__all__ = ["Settings"]


def _env_str(name: str, default: str) -> str:
    value = os.getenv(f"AJEEB_{name}")
    return value if value else default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(f"AJEEB_{name}")
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(f"AJEEB_{name}")
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    """User-tweakable knobs. Construct with ``Settings.from_env()``."""

    assistant_name: str = "Mr. Ajeeb"
    creator: str = "Keen Kanish"
    born_on: date = date(2020, 12, 30)

    # How the assistant addresses you. Empty by default so it stays neutral.
    address_as: str = ""

    # Text-to-speech
    tts_backend: str = "auto"  # auto | pyttsx3 | gtts | silent
    speech_rate: int = 165
    voice_hint: str = ""  # substring of a system voice name, e.g. "Zira"

    # Speech-to-text
    language: str = "en-IN"
    listen_timeout: int = 8  # seconds to wait for speech to start
    phrase_time_limit: int = 12  # max seconds of a single utterance

    # Network
    request_timeout: float = 10.0
    user_agent: str = "MrAjeeb/2.0 (https://github.com/keenkanish/ajeebpy)"

    # Skills
    home_town: str = ""  # assumed by the weather skill when no place is named
    notes_path: Path | None = None  # defaults to <data dir>/notes.json

    # Behaviour
    speak_replies: bool = True
    wikipedia_sentences: int = 2
    extra: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            assistant_name=_env_str("NAME", "Mr. Ajeeb"),
            creator=_env_str("CREATOR", "Keen Kanish"),
            address_as=_env_str("ADDRESS_AS", ""),
            tts_backend=_env_str("TTS", "auto").lower(),
            speech_rate=_env_int("SPEECH_RATE", 165),
            voice_hint=_env_str("VOICE", ""),
            language=_env_str("LANGUAGE", "en-IN"),
            listen_timeout=_env_int("LISTEN_TIMEOUT", 8),
            phrase_time_limit=_env_int("PHRASE_LIMIT", 12),
            home_town=_env_str("HOME_TOWN", ""),
            speak_replies=_env_bool("SPEAK", True),
            wikipedia_sentences=_env_int("WIKI_SENTENCES", 2),
        )

    @property
    def age_years(self) -> int:
        """Age of the assistant in whole years, computed instead of hard-coded."""
        today = date.today()
        years = today.year - self.born_on.year
        if (today.month, today.day) < (self.born_on.month, self.born_on.day):
            years -= 1
        return max(years, 0)

    def address(self, sentence: str) -> str:
        """Prefix a sentence with the configured form of address, if any."""
        if not self.address_as:
            return sentence
        return f"{self.address_as}, {sentence[0].lower()}{sentence[1:]}"
