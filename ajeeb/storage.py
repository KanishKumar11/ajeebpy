"""Small JSON-backed store so notes survive between sessions.

Deliberately boring: one file, atomic writes, and every failure degrades to an
empty list rather than taking the assistant down with it.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

__all__ = ["Note", "NoteBook", "data_dir"]


def data_dir() -> Path:
    """Where Mr. Ajeeb keeps its files (``AJEEB_HOME`` overrides)."""
    configured = os.getenv("AJEEB_HOME")
    if configured:
        return Path(configured).expanduser()
    try:
        return Path.home() / ".ajeeb"
    except RuntimeError:
        # No home directory (some containers and service accounts). Keeping the
        # notes beside the working directory beats refusing to start.
        log.debug("no home directory; keeping data in the working directory")
        return Path(".ajeeb")


@dataclass(frozen=True, slots=True)
class Note:
    text: str
    created: str

    @classmethod
    def new(cls, text: str) -> Note:
        return cls(text=text.strip(), created=datetime.now().isoformat(timespec="seconds"))

    @property
    def when(self) -> str:
        try:
            return datetime.fromisoformat(self.created).strftime("%d %b, %I:%M %p").lstrip("0")
        except ValueError:
            return self.created


class NoteBook:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_dir() / "notes.json"

    def all(self) -> list[Note]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, ValueError):
            log.warning("could not read %s; starting with an empty notebook", self.path)
            return []
        return [Note(**item) for item in raw if isinstance(item, dict) and "text" in item]

    def add(self, text: str) -> Note:
        note = Note.new(text)
        self._write([*self.all(), note])
        return note

    def clear(self) -> int:
        count = len(self.all())
        self._write([])
        return count

    def remove(self, index: int) -> Note:
        """Remove the 1-based ``index``-th note and return it."""
        notes = self.all()
        if not 1 <= index <= len(notes):
            raise IndexError(index)
        removed = notes.pop(index - 1)
        self._write(notes)
        return removed

    def _write(self, notes: list[Note]) -> None:
        payload = json.dumps([asdict(note) for note in notes], indent=2)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(payload, encoding="utf-8")
            temporary.replace(self.path)  # atomic: never a half-written notebook
        except OSError:
            log.warning("could not save notes to %s", self.path, exc_info=True)
