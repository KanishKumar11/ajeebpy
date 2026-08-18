"""The assistant itself: settings + skills + a voice, with no UI attached.

Both front-ends (terminal and Streamlit) drive this same object, which is why
the skills only had to be written once.
"""

from __future__ import annotations

import logging
import webbrowser

from ajeeb import skills as _skills  # noqa: F401  -- importing registers the skills
from ajeeb.config import Settings
from ajeeb.registry import Context, Reply, SkillRegistry, registry
from ajeeb.skills import greeting
from ajeeb.tts import Speaker, SilentSpeaker, make_speaker

log = logging.getLogger(__name__)

__all__ = ["Assistant"]


class Assistant:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        speaker: Speaker | None = None,
        skills: SkillRegistry | None = None,
        open_links: bool = False,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.skills = skills or registry
        self.speaker = speaker if speaker is not None else make_speaker(self.settings)
        self.open_links = open_links
        self.context = Context(self.settings)

    # -- conversation ------------------------------------------------------ #

    def greet(self, *, speak: bool = True) -> str:
        text = greeting(self.settings)
        if speak:
            self.say(text)
        return text

    def ask(self, text: str, *, speak: bool = True) -> Reply:
        """Answer one phrase. Never raises: a bad skill becomes an apology."""
        reply = self.skills.dispatch(text, self.context)
        if speak:
            self.say(reply.speech)
        if reply.url and self.open_links:
            self.open(reply.url)
        return reply

    def say(self, text: str) -> None:
        try:
            self.speaker.say(text)
        except Exception:  # speech is a nicety, never a reason to stop
            log.warning("speech failed; continuing silently", exc_info=True)
            self.speaker = SilentSpeaker()

    @staticmethod
    def open(url: str) -> None:
        try:
            webbrowser.open(url, new=2)
        except Exception:
            log.warning("could not open %s", url, exc_info=True)

    # -- lifecycle --------------------------------------------------------- #

    @property
    def history(self) -> list[tuple[str, Reply]]:
        return self.context.history

    def close(self) -> None:
        self.speaker.close()

    def __enter__(self) -> Assistant:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
