"""Routing rules: normalisation, priority, and never crashing on a bad skill."""

from __future__ import annotations

import unittest

from ajeeb.config import Settings
from ajeeb.registry import Context, Reply, SkillRegistry, normalise


def _reply(text: str):
    return lambda _ctx, _match: Reply(text)


class NormaliseTests(unittest.TestCase):
    def test_lowercases_and_collapses_whitespace(self):
        self.assertEqual(normalise("  What   IS  the TIME? "), "what is the time")

    def test_strips_the_wake_word(self):
        for phrase in ("hey ajeeb, flip a coin", "Mr. Ajeeb flip a coin", "ajeeb flip a coin"):
            self.assertEqual(normalise(phrase), "flip a coin", phrase)

    def test_survives_empty_input(self):
        self.assertEqual(normalise(""), "")
        self.assertEqual(normalise(None), "")


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = SkillRegistry()
        self.ctx = Context(Settings())

    def test_higher_priority_wins(self):
        self.registry.add("generic", [r"open .+"], _reply("generic"), priority=1)
        self.registry.add("specific", [r"^open youtube$"], _reply("specific"), priority=10)
        self.assertEqual(self.registry.dispatch("open youtube", self.ctx).speech, "specific")

    def test_registration_order_breaks_ties(self):
        self.registry.add("first", [r"hello"], _reply("first"))
        self.registry.add("second", [r"hello"], _reply("second"))
        self.assertEqual(self.registry.dispatch("hello", self.ctx).speech, "first")

    def test_unmatched_input_gets_a_polite_fallback(self):
        self.registry.add("x", [r"^zzz$"], _reply("x"))
        reply = self.registry.dispatch("something else entirely", self.ctx)
        self.assertIn("did not catch that", reply.speech)

    def test_a_typo_still_reaches_the_skill(self):
        self.registry.add("coin", [r"^flip a coin$"], _reply("ok"), examples=["flip a coin"])
        self.assertEqual(self.registry.dispatch("flip a coion", self.ctx).speech, "ok")

    def test_a_distant_phrase_is_not_guessed_at(self):
        self.registry.add("coin", [r"^flip a coin$"], _reply("ok"), examples=["flip a coin"])
        self.assertIn("did not catch", self.registry.dispatch("i had a rough day", self.ctx).speech)

    def test_a_guess_is_dropped_when_it_would_invent_an_argument(self):
        """Fuzzy-matching 'play shape of you' must not put words in your mouth."""
        self.registry.add(
            "play",
            [r"^play (?P<song>shape of you)$"],
            _reply("playing"),
            examples=["play shape of you"],
        )
        # Close enough to fuzzy-match the example, but acting on it would mean
        # deciding for the user which song they asked for.
        self.assertIsNone(self.registry.find("plai shape of yuo"))

    def test_fuzzy_matching_can_be_turned_off(self):
        self.registry.add("coin", [r"^flip a coin$"], _reply("ok"), examples=["flip a coin"])
        self.assertIsNone(self.registry.find("flip a coion", fuzzy=False))

    def test_a_broken_skill_does_not_kill_the_conversation(self):
        def explode(_ctx, _match):
            raise ValueError("boom")

        self.registry.add("bad", [r"^boom$"], explode)
        with self.assertLogs("ajeeb.registry", level="ERROR"):
            reply = self.registry.dispatch("boom", self.ctx)
        self.assertIn("went wrong", reply.speech)

    def test_handler_returning_none_still_replies(self):
        self.registry.add("quiet", [r"^quiet$"], lambda _c, _m: None)
        self.assertEqual(self.registry.dispatch("quiet", self.ctx).speech, "Done.")

    def test_history_records_answered_turns(self):
        self.registry.add("hi", [r"^hi$"], _reply("hello"))
        self.registry.dispatch("hi", self.ctx)
        self.assertEqual(len(self.ctx.history), 1)
        self.assertEqual(self.ctx.history[0][0], "hi")

    def test_a_skill_needs_at_least_one_pattern(self):
        with self.assertRaises(ValueError):
            self.registry.add("empty", [], _reply("never"))

    def test_named_groups_reach_the_handler(self):
        seen = {}

        def handler(_ctx, match):
            seen["topic"] = match.group("topic")
            return Reply("ok")

        self.registry.add("topic", [r"^about (?P<topic>.+)$"], handler)
        self.registry.dispatch("About Black Holes", self.ctx)
        self.assertEqual(seen["topic"], "black holes")


class ReplyTests(unittest.TestCase):
    def test_display_overrides_speech_for_screens(self):
        self.assertEqual(Reply("short", "long form").text, "long form")

    def test_text_falls_back_to_speech(self):
        self.assertEqual(Reply("only this").text, "only this")


if __name__ == "__main__":
    unittest.main()
