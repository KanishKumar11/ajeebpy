"""Every phrase the assistant used to understand must still route correctly."""

from __future__ import annotations

import calendar
import random
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from ajeeb import skills  # noqa: F401  -- registers the skills
from ajeeb.skills.web import SITES
from ajeeb.config import Settings
from ajeeb.registry import Context, registry

# Skills that would hit the network are checked by routing only, never dispatched.
ROUTING = [
    ("what is the time", "time"),
    ("what time is it", "time"),
    ("tell me the time", "time"),
    ("what is the date", "date"),
    ("what day is it", "date"),
    ("hey ajeeb, flip a coin", "coin"),
    ("roll a dice", "dice"),
    ("random number between 1 and 10", "random_number"),
    ("tell me a joke", "joke"),
    ("how old are you", "age"),
    ("who made you", "creator"),
    ("what is your name", "name"),
    ("who are you", "name"),
    ("are you in a relationship", "relationship"),
    ("thank you", "thanks"),
    ("hello", "greeting"),
    ("good morning", "greeting"),
    ("help", "help"),
    ("exit", "exit"),
    ("goodbye", "exit"),
    ("show calendar", "calendar"),
    ("calendar for march", "calendar"),
    ("open youtube", "open_site"),
    ("open github", "open_site"),
    ("play shape of you", "play"),
    ("play lofi beats on youtube", "play"),
    ("search youtube for guitar lessons", "youtube_search"),
    ("wikipedia black holes", "wikipedia"),
    ("who is ada lovelace", "wikipedia"),
    ("google best pizza", "search"),
    # phrasings the 2020 version (and the first rewrite) could not follow
    ("got the time?", "time"),
    ("time please", "time"),
    ("could you tell me what time it is", "time"),
    ("what's the day today", "date"),
    ("toss a coin for me", "coin"),
    ("gimme a random number", "random_number"),
    ("crack a joke", "joke"),
    ("say something funny", "joke"),
    ("launch youtube", "open_site"),
    ("take me to github", "open_site"),
    ("put on some lofi", "play"),
    ("i want to listen to arijit singh", "play"),
    ("look up quantum computing on wikipedia", "wikipedia"),
    ("explain recursion to me", "wikipedia"),
    ("how are you", "greeting"),
    # skills added after the first rewrite
    ("what is 12 times 8", "math"),
    ("whats 15% of 240", "math"),
    ("square root of 144", "math"),
    ("convert 10 km to miles", "convert"),
    ("convert 100 f to c", "convert"),
    ("what is the weather in chennai", "weather"),
    ("hows the weather", "weather"),
    ("is it raining in london", "weather"),
    ("define serendipity", "definition"),
    ("what does recursion mean", "definition"),
    ("what is the news", "news"),
    ("read me the headlines", "news"),
    ("what time is it in tokyo", "world_clock"),
    ("time in london", "world_clock"),
    ("how many days until christmas", "countdown"),
    ("days until 2027-01-01", "countdown"),
    ("generate a password", "password"),
    ("make a password with 24 characters", "password"),
    ("take a note buy milk", "note_add"),
    ("remind me to call mom", "note_add"),
    ("read my notes", "note_list"),
    ("delete note 1", "note_delete"),
    ("clear my notes", "note_delete"),
    ("roll a d20", "dice"),
]

# Things a command assistant should decline to guess at rather than misroute.
OUT_OF_SCOPE = [
    "i had a rough day",
    "what do you think about ai",
    "can you write me an email to my boss",
    "qwertyuiop zxcvbnm",
]


class RoutingTests(unittest.TestCase):
    def test_every_phrase_reaches_the_intended_skill(self):
        for phrase, expected in ROUTING:
            with self.subTest(phrase=phrase):
                hit = registry.find(phrase)
                self.assertIsNotNone(hit, f"{phrase!r} matched nothing")
                self.assertEqual(hit[0].name, expected)

    def test_out_of_scope_input_is_not_guessed_at(self):
        """A confidently wrong answer is worse than an honest "I did not catch that"."""
        for phrase in OUT_OF_SCOPE:
            with self.subTest(phrase=phrase):
                self.assertIsNone(registry.find(phrase))

    def test_every_skill_documents_itself(self):
        for entry in registry:
            with self.subTest(skill=entry.name):
                self.assertTrue(entry.help, f"{entry.name} has no help text")
                self.assertTrue(entry.examples, f"{entry.name} has no example")

    def test_examples_route_back_to_their_own_skill(self):
        for entry in registry:
            for example in entry.examples:
                with self.subTest(skill=entry.name, example=example):
                    hit = registry.find(example)
                    self.assertIsNotNone(hit)
                    self.assertEqual(hit[0].name, entry.name)


class OfflineSkillTests(unittest.TestCase):
    def setUp(self):
        self.ctx = Context(Settings())
        random.seed(1234)

    def ask(self, phrase):
        return registry.dispatch(phrase, self.ctx)

    def test_time_is_spoken_in_twelve_hour_form(self):
        speech = self.ask("what is the time").speech
        self.assertRegex(speech, r"The time is \d{1,2}:\d{2} (AM|PM)\.")

    def test_date_names_the_weekday(self):
        self.assertIn(datetime.now().strftime("%A"), self.ask("what is the date").speech)

    def test_address_prefix_is_applied_when_configured(self):
        self.ctx.settings.address_as = "Boss"
        self.assertTrue(self.ask("what is the time").speech.startswith("Boss, the time is"))

    def test_age_is_computed_not_hard_coded(self):
        settings = Settings(born_on=date(2020, 12, 30))
        expected = settings.age_years
        self.assertIn(f"{expected} years old", self.ask("how old are you").speech)

    def test_coin_lands_on_a_real_side(self):
        self.assertIn(self.ask("flip a coin").speech, ("It is heads.", "It is tails."))

    def test_dice_stays_within_range(self):
        for _ in range(25):
            value = int(self.ask("roll a dice").speech.split()[-1].rstrip("."))
            self.assertIn(value, range(1, 7))

    def test_dice_honours_a_custom_number_of_sides(self):
        value = int(self.ask("roll a dice with 20 sides").speech.split()[-1].rstrip("."))
        self.assertIn(value, range(1, 21))

    def test_random_number_respects_reversed_bounds(self):
        value = int(self.ask("random number between 10 and 1").speech.split()[-1].rstrip("."))
        self.assertIn(value, range(1, 11))

    def test_calendar_renders_the_requested_month(self):
        reply = self.ask("calendar for march 2027")
        self.assertEqual(reply.display, calendar.month(2027, 3))

    def test_unknown_month_is_reported_kindly(self):
        self.assertIn("do not know a month", self.ask("calendar for smarch").speech)

    def test_exit_sets_the_stop_flag(self):
        self.assertTrue(self.ask("goodbye").stop)

    def test_help_lists_the_other_skills(self):
        reply = self.ask("help")
        self.assertIn("Here is what I can do:", reply.display)
        self.assertGreaterEqual(reply.display.count("\n- "), 10)

    def test_open_site_returns_a_known_bookmark(self):
        self.assertEqual(self.ask("open github").url, "https://github.com")

    def test_open_site_handles_a_bare_domain(self):
        self.assertEqual(self.ask("open example.com").url, "https://example.com")

    def test_open_site_falls_back_to_a_search(self):
        self.assertIn("duckduckgo.com", self.ask("open some obscure place").url)

    def test_search_builds_an_encoded_query(self):
        self.assertEqual(self.ask("google best pizza").url, "https://duckduckgo.com/?q=best+pizza")

    def test_joke_says_something(self):
        self.assertGreater(len(self.ask("tell me a joke").speech), 10)

    def test_greeting_names_the_assistant_and_creator(self):
        speech = self.ask("hello").speech
        self.assertIn("Mr. Ajeeb", speech)
        self.assertIn("Keen Kanish", speech)


if __name__ == "__main__":
    unittest.main()


class NewSkillTests(unittest.TestCase):
    """The skills added in the rewrite, all exercised without a network."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        settings = Settings(notes_path=Path(self._tmp.name) / "notes.json")
        self.ctx = Context(settings)

    def ask(self, phrase):
        return registry.dispatch(phrase, self.ctx)

    # -- maths and units --------------------------------------------------- #

    def test_arithmetic_is_answered_with_the_working(self):
        self.assertIn("96", self.ask("what is 12 times 8").speech)

    def test_percentages(self):
        self.assertIn("36", self.ask("whats 15% of 240").speech)

    def test_a_bad_sum_explains_itself(self):
        self.assertIn("divide by zero", self.ask("what is 1 / 0").speech)

    def test_unit_conversion(self):
        self.assertIn("6.2137", self.ask("convert 10 km to miles").speech)

    def test_temperature_conversion(self):
        self.assertIn("37.7778", self.ask("convert 100 f to c").speech)

    def test_mixing_units_is_refused_politely(self):
        self.assertIn("different things", self.ask("convert 10 km to kg").speech)

    # -- passwords --------------------------------------------------------- #

    def test_password_is_the_requested_length_and_stays_off_the_speaker(self):
        reply = self.ask("make a password with 24 characters")
        secret = reply.display.strip("`")
        self.assertEqual(len(secret), 24)
        self.assertNotIn(secret, reply.speech, "a password must not be read aloud")

    def test_password_mixes_character_classes(self):
        secret = self.ask("generate a password").display.strip("`")
        self.assertTrue(any(c.islower() for c in secret))
        self.assertTrue(any(c.isupper() for c in secret))
        self.assertTrue(any(c.isdigit() for c in secret))

    def test_password_length_is_clamped_to_something_sensible(self):
        self.assertEqual(len(self.ask("password with 2 characters").display.strip("`")), 8)
        self.assertEqual(len(self.ask("password with 9999 characters").display.strip("`")), 128)

    def test_two_passwords_are_not_the_same(self):
        first = self.ask("generate a password").display
        self.assertNotEqual(first, self.ask("generate a password").display)

    # -- notes ------------------------------------------------------------- #

    def test_notes_are_saved_listed_and_deleted(self):
        self.assertIn("Noted", self.ask("take a note buy milk").speech)
        self.ask("remember that the bins go out on tuesday")
        listed = self.ask("read my notes")
        self.assertIn("buy milk", listed.speech)
        self.assertIn("bins go out", listed.speech)
        self.assertIn("buy milk", self.ask("delete note 1").speech)
        self.assertNotIn("buy milk", self.ask("read my notes").speech)

    def test_an_empty_notebook_says_so(self):
        self.assertIn("empty", self.ask("read my notes").speech)

    def test_notes_persist_on_disk(self):
        self.ask("take a note buy milk")
        fresh = Context(self.ctx.settings)
        self.assertIn("buy milk", registry.dispatch("read my notes", fresh).speech)

    def test_clearing_reports_the_count(self):
        self.ask("take a note one")
        self.ask("take a note two")
        self.assertIn("2 notes", self.ask("clear my notes").speech)

    def test_deleting_a_note_that_is_not_there(self):
        self.assertIn("no note number 7", self.ask("delete note 7").speech)

    # -- clock ------------------------------------------------------------- #

    def test_world_clock_knows_a_city(self):
        reply = self.ask("what time is it in tokyo")
        self.assertRegex(reply.speech, r"It is \d{1,2}:\d{2} (AM|PM) in Tokyo")
        self.assertIn("Asia/Tokyo", reply.display)

    def test_world_clock_admits_when_it_does_not_know(self):
        self.assertIn("do not know the timezone", self.ask("what time is it in atlantis").speech)

    def test_countdown_to_a_holiday(self):
        reply = self.ask("how many days until christmas")
        self.assertRegex(reply.speech, r"(\d+ days until Christmas|Christmas is today)")

    def test_countdown_to_an_explicit_date(self):
        target = date.today() + timedelta(days=10)
        self.assertIn("10 days until", self.ask(f"days until {target:%Y-%m-%d}").speech)

    def test_countdown_looks_backwards_too(self):
        past = date.today() - timedelta(days=5)
        self.assertIn("5 days ago", self.ask(f"days until {past:%Y-%m-%d}").speech)

    def test_countdown_admits_defeat_on_gibberish(self):
        self.assertIn("could not work out", self.ask("how many days until blorp").speech)
