"""A tiny intent registry: the modern replacement for a long ``if/elif`` chain.

Each skill declares the phrasings it answers to as regular expressions. The
registry picks the highest-priority pattern that matches and hands the regex
``Match`` to the handler, so skills receive parsed arguments instead of
re-slicing the raw string.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from difflib import SequenceMatcher, get_close_matches
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ajeeb.config import Settings

log = logging.getLogger(__name__)

__all__ = [
    "Context",
    "Handler",
    "Reply",
    "Skill",
    "SkillRegistry",
    "normalise",
    "phrase",
    "registry",
    "skill",
]


@dataclass(slots=True)
class Reply:
    """What the assistant says back.

    ``speech`` is spoken aloud; ``display`` is what a screen should show when it
    differs (long Wikipedia extracts, tables...). ``url`` lets a skill hand a link
    to the front-end instead of opening a browser itself -- the terminal opens it,
    the web UI renders it as a link.
    """

    speech: str
    display: str | None = None
    url: str | None = None
    stop: bool = False

    @property
    def text(self) -> str:
        return self.display if self.display is not None else self.speech


@dataclass(slots=True)
class Context:
    """Everything a handler is allowed to reach for.

    ``state`` is a scratch space for skills that need to keep something between
    turns (an open notebook, a cached client) without reaching for a global.
    """

    settings: Settings
    history: list[tuple[str, Reply]] = field(default_factory=list)
    state: dict[str, object] = field(default_factory=dict)


Handler = Callable[[Context, "re.Match[str]"], Reply | None]


@dataclass(frozen=True, slots=True)
class Skill:
    name: str
    patterns: tuple[re.Pattern[str], ...]
    handler: Handler
    help: str = ""
    examples: tuple[str, ...] = ()
    priority: int = 0

    def match(self, text: str) -> re.Match[str] | None:
        for pattern in self.patterns:
            found = pattern.search(text)
            if found:
                return found
        return None


class SkillRegistry:
    """Holds the skills and routes a phrase to one of them."""

    def __init__(self) -> None:
        self._skills: list[Skill] = []
        self._sorted = True

    def __iter__(self) -> Iterator[Skill]:
        return iter(self.skills)

    def __len__(self) -> int:
        return len(self._skills)

    @property
    def skills(self) -> Sequence[Skill]:
        if not self._sorted:
            # Stable sort keeps registration order inside a priority band.
            self._skills.sort(key=lambda s: -s.priority)
            self._sorted = True
        return tuple(self._skills)

    def add(
        self,
        name: str,
        patterns: Iterable[str],
        handler: Handler,
        *,
        help: str = "",
        examples: Iterable[str] = (),
        priority: int = 0,
    ) -> Skill:
        compiled = tuple(re.compile(p, re.IGNORECASE) for p in patterns)
        if not compiled:
            raise ValueError(f"skill {name!r} needs at least one pattern")
        entry = Skill(name, compiled, handler, help, tuple(examples), priority)
        self._skills.append(entry)
        self._sorted = False
        return entry

    def register(
        self,
        name: str,
        *patterns: str,
        help: str = "",
        examples: Iterable[str] = (),
        priority: int = 0,
    ) -> Callable[[Handler], Handler]:
        """Decorator form of :meth:`add`."""

        def decorate(handler: Handler) -> Handler:
            self.add(
                name,
                patterns,
                handler,
                help=help,
                examples=examples,
                priority=priority,
            )
            return handler

        return decorate

    def find(self, text: str, *, fuzzy: bool = True) -> tuple[Skill, re.Match[str]] | None:
        cleaned = normalise(text)
        if not cleaned:
            return None
        for entry in self.skills:
            found = entry.match(cleaned)
            if found:
                return entry, found
        return self._find_despite_typos(cleaned) if fuzzy else None

    def _find_despite_typos(self, cleaned: str) -> tuple[Skill, re.Match[str]] | None:
        """Second pass for misheard or mistyped input: 'flip a coion'.

        This is deliberately typo-tolerance and not paraphrase-matching. A loose
        similarity score would drag unrelated sentences ("I had a rough day")
        into the nearest skill, and a confidently wrong answer is worse than an
        honest "I did not catch that".
        """
        best: tuple[float, Skill, str] | None = None
        for entry in self.skills:
            for example in entry.examples:
                score = SequenceMatcher(None, cleaned, normalise(example)).ratio()
                if score >= FUZZY_CUTOFF and (best is None or score > best[0]):
                    best = (score, entry, example)
        if best is None:
            return None

        _score, entry, example = best
        # Re-match against the canonical example so the handler still receives a
        # real Match. If that fills in a capture group we would be inventing an
        # argument the user never said, so the guess is dropped instead.
        found = entry.match(normalise(example))
        if found is None or any(found.groupdict().values()):
            return None
        log.debug("fuzzy match: %r -> %s (via %r)", cleaned, entry.name, example)
        return entry, found

    def dispatch(self, text: str, ctx: Context) -> Reply:
        """Route ``text`` to a skill and always come back with something to say."""
        hit = self.find(text)
        if hit is None:
            return self._fallback(text)

        entry, found = hit
        try:
            reply = entry.handler(ctx, found)
        except Exception:  # a broken skill must not kill the conversation
            log.exception("skill %r failed on %r", entry.name, text)
            return Reply("Sorry, that one went wrong on my side. Try again?")

        if reply is None:
            reply = Reply("Done.")
        ctx.history.append((text, reply))
        return reply

    def _fallback(self, text: str) -> Reply:
        suggestion = self.suggest(text)
        if suggestion:
            return Reply(f"I did not catch that. Did you mean {suggestion!r}?")
        return Reply(
            "I did not catch that. Say 'help' for the list, "
            "or put 'search' in front to look it up on the web."
        )

    def suggest(self, text: str) -> str | None:
        """Best-effort 'did you mean' using the registered examples."""
        pool = [example for entry in self.skills for example in entry.examples]
        close = get_close_matches(normalise(text), pool, n=1, cutoff=0.5)
        return close[0] if close else None


FUZZY_CUTOFF = 0.78
"""How close a phrase must be to a known example before we act on the guess."""

# Filler people put around a request. Absorbing it here means each skill can
# describe the *core* of what it answers to instead of spelling out every
# combination of "hey", "could you", "for me" and "please".
_LEAD = (
    r"(?:(?:hey|hi|hello|ok|okay|so|um|uh|now|just|quickly|please|"
    r"can you|could you|would you|will you|do you|do you know|you got|got|"
    r"tell me|give me|gimme|show me|get me|find me|say|i need|i want to|i wanna|"
    r"i would like to|i'?d like to|let'?s|lets|whats|what'?s)\s+)*"
)
_TAIL = (
    r"(?:\s+(?:please|for me|now|rn|right now|today|thanks|thank you|"
    r"ajeeb|mr\.? ajeeb))*"
)


def phrase(core: str) -> str:
    """Turn the core of a request into a pattern tolerant of polite padding.

    ``phrase(r"flip a coin")`` also matches "hey could you flip a coin for me
    please". Anchoring both ends keeps a skill from firing on a stray word in
    the middle of an unrelated sentence.
    """
    return rf"^{_LEAD}(?:{core}){_TAIL}$"


_WHITESPACE = re.compile(r"\s+")
_FILLER = re.compile(r"^(?:hey |ok |okay |hi )?(?:ajeeb|mr\.? ajeeb)[,\s]+", re.IGNORECASE)


def normalise(text: str) -> str:
    """Lower-case, collapse whitespace and drop a leading wake word."""
    cleaned = _WHITESPACE.sub(" ", (text or "").strip().lower())
    cleaned = _FILLER.sub("", cleaned, count=1)
    return cleaned.strip(" .!?,")


registry = SkillRegistry()
skill = registry.register
