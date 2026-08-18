"""Network helpers, exercised with stubbed HTTP so the suite stays offline."""

from __future__ import annotations

import unittest
from unittest import mock

import requests

from ajeeb.services import (
    LookupError_,
    NotFound,
    define,
    resolve_youtube_video,
    sentences,
    top_stories,
    weather,
    wikipedia_summary,
    youtube_search_url,
)


class FakeResponse:
    """Stands in for ``requests.Response``, including how it reports failures."""

    def __init__(self, payload=None, text="", status=200):
        self._payload = payload
        self.text = text
        self.status_code = status

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            # requests attaches the response to the error; the 404 handling
            # depends on it, so the fake has to do the same.
            raise requests.HTTPError(f"status {self.status_code}", response=self)


class FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.headers = {}
        self.closed = False
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        result = self._responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def close(self):
        self.closed = True


class SentenceTests(unittest.TestCase):
    def test_takes_the_requested_number_of_sentences(self):
        self.assertEqual(sentences("One. Two! Three? Four.", 2), "One. Two!")

    def test_short_text_is_returned_whole(self):
        self.assertEqual(sentences("Only one.", 5), "Only one.")

    def test_zero_means_everything(self):
        self.assertEqual(sentences("One. Two.", 0), "One. Two.")


class WikipediaTests(unittest.TestCase):
    def _run(self, responses):
        session = FakeSession(responses)
        with mock.patch("ajeeb.services._session", return_value=session):
            return session, wikipedia_summary("ada lovelace")

    def test_returns_the_lead_extract(self):
        search = FakeResponse({"query": {"search": [{"title": "Ada Lovelace"}]}})
        summary = FakeResponse(
            {
                "title": "Ada Lovelace",
                "extract": "She wrote the first algorithm. She is celebrated widely.",
                "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Ada_Lovelace"}},
            }
        )
        session, article = self._run([search, summary])
        self.assertEqual(article.title, "Ada Lovelace")
        self.assertIn("first algorithm", article.extract)
        self.assertEqual(article.url, "https://en.wikipedia.org/wiki/Ada_Lovelace")
        self.assertTrue(session.closed, "the HTTP session must be closed")

    def test_no_results_is_reported_not_raised_as_a_crash(self):
        with self.assertRaises(LookupError_) as caught:
            self._run([FakeResponse({"query": {"search": []}})])
        self.assertIn("no article", str(caught.exception))

    def test_an_empty_topic_is_rejected_before_any_request(self):
        with self.assertRaises(LookupError_):
            wikipedia_summary("   ")

    def test_network_failure_becomes_a_friendly_message(self):
        with self.assertRaises(LookupError_) as caught:
            self._run([requests.ConnectionError("offline")])
        self.assertIn("could not reach Wikipedia", str(caught.exception))

    def test_a_page_without_a_summary_is_explained(self):
        search = FakeResponse({"query": {"search": [{"title": "Ada Lovelace"}]}})
        with self.assertRaises(LookupError_) as caught:
            self._run([search, FakeResponse({"title": "Ada Lovelace", "extract": "  "})])
        self.assertIn("no summary", str(caught.exception))


class YouTubeTests(unittest.TestCase):
    def test_search_url_is_percent_encoded(self):
        self.assertEqual(
            youtube_search_url("lofi beats & chill"),
            "https://www.youtube.com/results?search_query=lofi+beats+%26+chill",
        )

    def test_first_result_is_turned_into_a_watch_url(self):
        page = 'junk {"videoId":"dQw4w9WgXcQ"} more junk'
        with mock.patch("ajeeb.services.requests.get", return_value=FakeResponse(text=page)):
            url = resolve_youtube_video("never gonna give you up")
        self.assertEqual(url, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    def test_missing_video_id_falls_back_to_the_results_page(self):
        with mock.patch("ajeeb.services.requests.get", return_value=FakeResponse(text="nothing")):
            url = resolve_youtube_video("obscure song")
        self.assertEqual(url, youtube_search_url("obscure song"))

    def test_network_failure_falls_back_to_the_results_page(self):
        with mock.patch("ajeeb.services.requests.get", side_effect=requests.Timeout("slow")):
            url = resolve_youtube_video("obscure song")
        self.assertEqual(url, youtube_search_url("obscure song"))

    def test_an_empty_query_is_rejected(self):
        with self.assertRaises(LookupError_):
            resolve_youtube_video("")


if __name__ == "__main__":
    unittest.main()


class WeatherTests(unittest.TestCase):
    GEOCODE = {
        "results": [
            {"name": "Chennai", "country": "India", "latitude": 13.1, "longitude": 80.3}
        ]
    }
    FORECAST = {
        "current": {
            "temperature_2m": 31.4,
            "apparent_temperature": 35.2,
            "weather_code": 2,
            "wind_speed_10m": 14.3,
        }
    }

    def _run(self, responses, place="chennai"):
        with mock.patch("ajeeb.services.requests.get", side_effect=responses):
            return weather(place)

    def test_current_conditions_are_rounded_for_speech(self):
        report = self._run([FakeResponse(self.GEOCODE), FakeResponse(self.FORECAST)])
        self.assertEqual(report.place, "Chennai, India")
        self.assertEqual(report.description, "partly cloudy")
        self.assertEqual(report.temperature, 31)
        self.assertEqual(report.feels_like, 35)
        self.assertEqual(report.unit, "C")

    def test_an_unknown_weather_code_still_answers(self):
        forecast = {"current": dict(self.FORECAST["current"], weather_code=1234)}
        report = self._run([FakeResponse(self.GEOCODE), FakeResponse(forecast)])
        self.assertEqual(report.description, "hard to describe")

    def test_an_unknown_place_is_reported(self):
        with self.assertRaises(LookupError_) as caught:
            self._run([FakeResponse({"results": []})], place="atlantis")
        self.assertIn("could not find a place", str(caught.exception))

    def test_an_empty_place_is_rejected_before_any_request(self):
        with self.assertRaises(LookupError_):
            weather("  ")

    def test_a_missing_reading_is_reported(self):
        with self.assertRaises(LookupError_) as caught:
            self._run([FakeResponse(self.GEOCODE), FakeResponse({"current": {}})])
        self.assertIn("No current readings", str(caught.exception))


class DefinitionTests(unittest.TestCase):
    WIKTIONARY = {
        "en": [
            {
                "partOfSpeech": "Noun",
                "definitions": [
                    {
                        "definition": 'The <a href="/wiki/x">phenomenon</a> of a lucky find.',
                        "examples": ["<i>Serendipity</i> struck."],
                    }
                ],
            }
        ]
    }

    def test_html_from_wiktionary_is_stripped(self):
        with mock.patch("ajeeb.services.requests.get", return_value=FakeResponse(self.WIKTIONARY)):
            found = define("serendipity")
        self.assertEqual(found.meaning, "The phenomenon of a lucky find.")
        self.assertEqual(found.part_of_speech, "noun")
        self.assertEqual(found.example, "Serendipity struck.")

    def test_the_backup_dictionary_is_used_when_wiktionary_is_down(self):
        backup = [{"word": "x", "meanings": [{"partOfSpeech": "noun",
                                              "definitions": [{"definition": "a thing"}]}]}]
        responses = [FakeResponse(status=502), FakeResponse(backup)]
        with mock.patch("ajeeb.services.requests.get", side_effect=responses):
            self.assertEqual(define("x").meaning, "a thing")

    def test_a_word_neither_dictionary_knows(self):
        responses = [FakeResponse(status=404), FakeResponse(status=404)]
        with mock.patch("ajeeb.services.requests.get", side_effect=responses):
            with self.assertRaises(NotFound):
                define("qwertyuiopx")

    def test_a_404_beats_an_unreachable_backup(self):
        """Wiktionary said 'no such word'; do not blame the network for it."""
        responses = [FakeResponse(status=404), FakeResponse(status=502)]
        with mock.patch("ajeeb.services.requests.get", side_effect=responses):
            with self.assertRaises(NotFound):
                define("qwertyuiopx")

    def test_both_dictionaries_unreachable_says_so(self):
        responses = [FakeResponse(status=502), FakeResponse(status=503)]
        with mock.patch("ajeeb.services.requests.get", side_effect=responses):
            with self.assertRaises(LookupError_) as caught:
                define("serendipity")
        self.assertIn("could not reach a dictionary", str(caught.exception))


class NewsTests(unittest.TestCase):
    def test_headlines_are_collected(self):
        responses = [
            FakeResponse([1, 2, 3, 4]),
            FakeResponse({"title": "First", "url": "https://one.example", "score": 120}),
            FakeResponse({"title": "Second", "score": 80}),
        ]
        with mock.patch("ajeeb.services.requests.get", side_effect=responses):
            stories = top_stories(2)
        self.assertEqual([s.title for s in stories], ["First", "Second"])
        self.assertEqual(stories[0].score, 120)
        self.assertIn("news.ycombinator.com", stories[1].url, "a text post links to the thread")

    def test_items_without_a_title_are_skipped(self):
        responses = [FakeResponse([1, 2]), FakeResponse({}), FakeResponse({"title": "Real"})]
        with mock.patch("ajeeb.services.requests.get", side_effect=responses):
            self.assertEqual([s.title for s in top_stories(2)], ["Real"])

    def test_an_empty_front_page_is_reported(self):
        with mock.patch("ajeeb.services.requests.get", return_value=FakeResponse([])):
            with self.assertRaises(LookupError_):
                top_stories(3)
