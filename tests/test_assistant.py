"""The assistant object and the terminal front-end."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest import mock

from ajeeb import Assistant, Settings
from ajeeb import cli
from ajeeb.cli import build_parser, main
from ajeeb.registry import Context, Reply, SkillRegistry
from ajeeb.tts import SilentSpeaker, make_speaker


class RecordingSpeaker:
    name = "recording"

    def __init__(self, fail: bool = False):
        self.said: list[str] = []
        self.closed = False
        self.fail = fail

    def say(self, text: str) -> None:
        if self.fail:
            raise RuntimeError("audio device exploded")
        self.said.append(text)

    def close(self) -> None:
        self.closed = True


def _registry() -> SkillRegistry:
    registry = SkillRegistry()
    registry.add("ping", [r"^ping$"], lambda _c, _m: Reply("pong"))
    registry.add("link", [r"^link$"], lambda _c, _m: Reply("here", url="https://example.com"))
    registry.add("bye", [r"^bye$"], lambda _c, _m: Reply("goodbye", stop=True))
    return registry


class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.speaker = RecordingSpeaker()
        self.assistant = Assistant(Settings(), speaker=self.speaker, skills=_registry())

    def test_it_answers_and_speaks(self):
        self.assertEqual(self.assistant.ask("ping").speech, "pong")
        self.assertEqual(self.speaker.said, ["pong"])

    def test_speaking_can_be_suppressed_per_turn(self):
        self.assistant.ask("ping", speak=False)
        self.assertEqual(self.speaker.said, [])

    def test_links_stay_closed_unless_asked_for(self):
        with mock.patch("ajeeb.assistant.webbrowser.open") as opened:
            self.assistant.ask("link")
        opened.assert_not_called()

    def test_links_open_when_enabled(self):
        assistant = Assistant(Settings(), speaker=self.speaker, skills=_registry(), open_links=True)
        with mock.patch("ajeeb.assistant.webbrowser.open") as opened:
            assistant.ask("link")
        opened.assert_called_once()
        self.assertEqual(opened.call_args.args[0], "https://example.com")

    def test_a_broken_speaker_downgrades_to_silence(self):
        assistant = Assistant(Settings(), speaker=RecordingSpeaker(fail=True), skills=_registry())
        with self.assertLogs("ajeeb.assistant", level="WARNING"):
            assistant.ask("ping")
        self.assertIsInstance(assistant.speaker, SilentSpeaker)
        assistant.ask("ping")  # still answering, just quietly

    def test_history_is_kept(self):
        self.assistant.ask("ping")
        self.assistant.ask("bye")
        self.assertEqual([turn[0] for turn in self.assistant.history], ["ping", "bye"])

    def test_it_closes_its_speaker(self):
        with Assistant(Settings(), speaker=self.speaker, skills=_registry()):
            pass
        self.assertTrue(self.speaker.closed)

    def test_greeting_mentions_the_creator(self):
        self.assertIn("Keen Kanish", self.assistant.greet(speak=False))


class SpeakerFactoryTests(unittest.TestCase):
    def test_muted_settings_give_a_silent_speaker(self):
        self.assertIsInstance(make_speaker(Settings(speak_replies=False)), SilentSpeaker)

    def test_a_missing_backend_degrades_instead_of_crashing(self):
        patched = mock.patch("ajeeb.tts.Pyttsx3Speaker", side_effect=ImportError("x"))
        with patched, self.assertLogs("ajeeb.tts", level="WARNING"):
            speaker = make_speaker(Settings(tts_backend="pyttsx3"))
        self.assertIsInstance(speaker, SilentSpeaker)


class CliTests(unittest.TestCase):
    def test_ask_answers_one_phrase_and_exits(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(["--ask", "flip a coin", "--no-speak"])
        self.assertEqual(code, 0)
        self.assertIn("It is", out.getvalue())

    def test_list_skills_prints_the_catalogue(self):
        out = io.StringIO()
        with redirect_stdout(out):
            main(["--list-skills"])
        self.assertIn("wikipedia", out.getvalue())

    def test_the_text_loop_stops_on_exit(self):
        out = io.StringIO()
        typed = mock.patch("builtins.input", side_effect=["flip a coin", "exit"])
        with typed, redirect_stdout(out):
            code = main(["--no-speak"])
        self.assertEqual(code, 0)
        self.assertIn("signing off", out.getvalue())

    def test_ctrl_c_leaves_politely(self):
        out = io.StringIO()
        with mock.patch("builtins.input", side_effect=KeyboardInterrupt), redirect_stdout(out):
            self.assertEqual(main(["--no-speak"]), 0)

    def test_characters_the_console_cannot_print_are_folded(self):
        class AsciiOnly:
            encoding = "ascii"

        with mock.patch.object(cli.sys, "stdout", AsciiOnly()):
            self.assertEqual(cli.for_console("31°C — warm"), "31C - warm")

    def test_printable_text_is_left_alone(self):
        self.assertEqual(cli.for_console("plain ascii"), "plain ascii")

    def test_flags_are_parsed(self):
        args = build_parser().parse_args(["--voice", "--rate", "200", "--voice-name", "Zira"])
        self.assertTrue(args.voice)
        self.assertEqual(args.rate, 200)
        self.assertEqual(args.voice_name, "Zira")


class ContextTests(unittest.TestCase):
    def test_each_context_gets_its_own_history(self):
        self.assertIsNot(Context(Settings()).history, Context(Settings()).history)


if __name__ == "__main__":
    unittest.main()
