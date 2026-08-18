"""Kept so that ``python keen.py`` still works.

The 2020 script that lived here grew into the ``ajeeb`` package. Use one of:

    python -m ajeeb              # terminal, type at it
    python -m ajeeb --voice      # terminal, microphone
    streamlit run app.py         # browser chat with a mic button
"""

from __future__ import annotations

import sys

from ajeeb.cli import main

if __name__ == "__main__":
    print(__doc__.strip(), file=sys.stderr)
    print(file=sys.stderr)
    raise SystemExit(main())
