"""Mr. Ajeeb - a voice assistant, rebuilt.

Originally a single 150-line script from 2020; now a small package with a
UI-agnostic core, a terminal front-end and a Streamlit web front-end.
"""

from __future__ import annotations

from ajeeb.assistant import Assistant
from ajeeb.config import Settings
from ajeeb.registry import Context, Reply, Skill, SkillRegistry, registry, skill

__version__ = "2.0.0"
__all__ = [
    "Assistant",
    "Context",
    "Reply",
    "Settings",
    "Skill",
    "SkillRegistry",
    "__version__",
    "registry",
    "skill",
]
