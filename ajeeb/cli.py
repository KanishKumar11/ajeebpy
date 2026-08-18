"""Terminal front-end.

    ajeeb                 # type at it (works everywhere, no microphone needed)
    ajeeb --voice         # listen through the microphone
    ajeeb --ask "time"    # answer one thing and exit, handy for scripts
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

from ajeeb import __version__
from ajeeb.assistant import Assistant
from ajeeb.config import Settings
from ajeeb.registry import Reply
from ajeeb.stt import MicrophoneUnavailable, listen, microphone_ready

log = logging.getLogger(__name__)

__all__ = ["main", "build_parser"]

PROMPT = "you > "

# Windows consoles still default to cp1252, where an em dash or a degree sign
# prints as "?". The web UI keeps the typography; the terminal gets a fold-down.
_FOLD = str.maketrans({
    "—": "-", "–": "-", "°": "", "‘": "'", "’": "'",
    "“": '"', "”": '"', "…": "...", "×": "x", "→": "->",
})


def for_console(text: str) -> str:
    """Fold characters this console cannot print, instead of showing '?'."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        text.encode(encoding)
    except (UnicodeEncodeError, LookupError):
        folded = text.translate(_FOLD)
        return folded.encode(encoding, "replace").decode(encoding, "replace")
    return text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ajeeb",
        description="Mr. Ajeeb, a voice assistant.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Say 'help' at the prompt to list the skills, 'exit' to leave.",
    )
    parser.add_argument("--voice", action="store_true", help="listen on the microphone")
    parser.add_argument("--ask", metavar="TEXT", help="answer one phrase, then exit")
    parser.add_argument("--no-speak", action="store_true", help="stay quiet, print only")
    parser.add_argument("--open-links", action="store_true", help="open results in a browser")
    parser.add_argument("--list-skills", action="store_true", help="list the skills and exit")
    parser.add_argument("--voice-name", metavar="NAME", help="pick a system voice by name")
    parser.add_argument("--rate", type=int, metavar="WPM", help="speaking rate")
    parser.add_argument("-v", "--verbose", action="store_true", help="show debug logging")
    parser.add_argument("--version", action="version", version=f"Mr. Ajeeb {__version__}")
    return parser


def _settings_from(args: argparse.Namespace) -> Settings:
    settings = Settings.from_env()
    if args.no_speak:
        settings.speak_replies = False
    if args.voice_name:
        settings.voice_hint = args.voice_name
    if args.rate:
        settings.speech_rate = args.rate
    return settings


def _show(reply: Reply) -> None:
    print(f"ajeeb > {for_console(reply.text)}")
    if reply.url:
        print(f"        {reply.url}")


def _run_text_loop(assistant: Assistant) -> int:
    print("(type 'help' for the skill list, 'exit' to quit)\n")
    while True:
        try:
            query = input(PROMPT).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            assistant.say("Goodbye!")
            return 0
        if not query:
            continue
        reply = assistant.ask(query)
        _show(reply)
        if reply.stop:
            return 0


def _run_voice_loop(assistant: Assistant) -> int:
    if not microphone_ready():
        print("No microphone detected. Falling back to typing.\n", file=sys.stderr)
        return _run_text_loop(assistant)

    print("(listening -- say 'exit' to quit, Ctrl+C to stop)\n")
    while True:
        try:
            heard = listen(assistant.settings, on_listening=lambda: print("listening...", end="\r"))
        except MicrophoneUnavailable as exc:
            print(f"\n{exc}\nFalling back to typing.\n", file=sys.stderr)
            return _run_text_loop(assistant)
        except KeyboardInterrupt:
            print()
            assistant.say("Goodbye!")
            return 0

        if not heard:
            print(f"ajeeb > {heard.error}")
            continue

        print(f"{PROMPT}{heard.text}")
        reply = assistant.ask(heard.text)
        _show(reply)
        if reply.stop:
            return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    settings = _settings_from(args)

    if args.list_skills:
        from ajeeb.skills import registry

        for entry in registry:
            if entry.help:
                example = entry.examples[0] if entry.examples else ""
                print(f"{entry.name:16} {entry.help}" + (f"  e.g. {example!r}" if example else ""))
        return 0

    with Assistant(settings, open_links=args.open_links or args.voice) as assistant:
        if args.ask:
            _show(assistant.ask(args.ask))
            return 0

        print(f"ajeeb > {assistant.greet()}")
        return _run_voice_loop(assistant) if args.voice else _run_text_loop(assistant)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
