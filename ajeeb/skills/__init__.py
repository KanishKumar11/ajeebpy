"""Everything Mr. Ajeeb can do, grouped by subject.

Importing this package registers every skill on the shared registry. Each
module is small on purpose: adding a skill means one function in one file.
"""

from __future__ import annotations

from ajeeb.registry import registry
from ajeeb.skills import chitchat, clock, tools, web
from ajeeb.skills.chitchat import greeting
from ajeeb.skills.web import SITES

__all__ = ["SITES", "chitchat", "clock", "greeting", "registry", "tools", "web"]
