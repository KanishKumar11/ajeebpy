"""Network helpers.

The 2020 version leaned on the ``wikipedia`` package (unmaintained since 2014)
and ``pywhatkit`` (which drives YouTube by faking keystrokes). Both are replaced
here by plain HTTPS calls, so there is one small dependency, no GUI automation,
and every function is easy to test.
"""

from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from urllib.parse import quote_plus

import requests

log = logging.getLogger(__name__)

__all__ = [
    "LookupError_",
    "NotFound",
    "WikipediaArticle",
    "wikipedia_summary",
    "youtube_search_url",
    "resolve_youtube_video",
    "sentences",
]

WIKI_API = "https://{lang}.wikipedia.org/w/api.php"
WIKI_SUMMARY = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
YOUTUBE_RESULTS = "https://www.youtube.com/results?search_query={query}"
YOUTUBE_WATCH = "https://www.youtube.com/watch?v={video_id}"

_VIDEO_ID = re.compile(r'"videoId":"([A-Za-z0-9_-]{11})"')
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_TAGS = re.compile(r"<[^>]+>")


def _strip_markup(text: str) -> str:
    """Wiktionary returns HTML; the assistant wants a sentence."""
    return re.sub(r"\s+", " ", html.unescape(_TAGS.sub("", text or ""))).strip()


class LookupError_(RuntimeError):
    """Raised when a lookup fails for a reason worth telling the user about."""


class NotFound(LookupError_):
    """The service answered, and the answer was "no such thing"."""


@dataclass(frozen=True, slots=True)
class WikipediaArticle:
    title: str
    extract: str
    url: str


def sentences(text: str, count: int) -> str:
    """First ``count`` sentences of ``text`` (whole text if it is shorter)."""
    if count <= 0:
        return text.strip()
    parts = _SENTENCE_END.split(text.strip())
    return " ".join(parts[:count]).strip()


def _session(user_agent: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent, "Accept-Encoding": "gzip"})
    return session


def wikipedia_summary(
    topic: str,
    *,
    lang: str = "en",
    timeout: float = 10.0,
    user_agent: str = "MrAjeeb/2.0",
) -> WikipediaArticle:
    """Search Wikipedia and return the lead extract of the best match."""
    topic = topic.strip()
    if not topic:
        raise LookupError_("Tell me what to look up on Wikipedia.")

    session = _session(user_agent)
    try:
        search = session.get(
            WIKI_API.format(lang=lang),
            params={
                "action": "query",
                "list": "search",
                "srsearch": topic,
                "srlimit": 1,
                "format": "json",
            },
            timeout=timeout,
        )
        search.raise_for_status()
        hits = search.json().get("query", {}).get("search", [])
        if not hits:
            raise LookupError_(f"Wikipedia has no article about {topic}.")

        title = hits[0]["title"]
        summary = session.get(
            WIKI_SUMMARY.format(lang=lang, title=quote_plus(title.replace(" ", "_"))),
            timeout=timeout,
        )
        summary.raise_for_status()
        data = summary.json()
    except requests.RequestException as exc:
        log.debug("wikipedia request failed: %s", exc)
        raise LookupError_("I could not reach Wikipedia just now.") from exc
    except ValueError as exc:  # bad JSON
        raise LookupError_("Wikipedia sent something I could not read.") from exc
    finally:
        session.close()

    extract = (data.get("extract") or "").strip()
    if not extract:
        raise LookupError_(f"I found {title}, but there is no summary to read out.")

    return WikipediaArticle(
        title=data.get("title", title),
        extract=extract,
        url=data.get("content_urls", {}).get("desktop", {}).get("page", "")
        or f"https://{lang}.wikipedia.org/wiki/{quote_plus(title.replace(' ', '_'))}",
    )


def youtube_search_url(query: str) -> str:
    return YOUTUBE_RESULTS.format(query=quote_plus(query.strip()))


def resolve_youtube_video(
    query: str,
    *,
    timeout: float = 10.0,
    user_agent: str = "MrAjeeb/2.0",
) -> str:
    """URL of the first YouTube result, falling back to the results page."""
    query = query.strip()
    if not query:
        raise LookupError_("Tell me what to play.")

    fallback = youtube_search_url(query)
    try:
        response = requests.get(
            fallback,
            headers={"User-Agent": user_agent, "Accept-Language": "en-US,en;q=0.9"},
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        log.debug("youtube lookup failed: %s", exc)
        return fallback

    found = _VIDEO_ID.search(response.text)
    return YOUTUBE_WATCH.format(video_id=found.group(1)) if found else fallback


# --------------------------------------------------------------------------- #
# Weather, dictionary and news -- all key-free public APIs
# --------------------------------------------------------------------------- #

GEOCODE_API = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_API = "https://api.open-meteo.com/v1/forecast"
WIKTIONARY_API = "https://en.wiktionary.org/api/rest_v1/page/definition/{word}"
DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"

# https://open-meteo.com/en/docs -- WMO weather interpretation codes
WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "foggy", 48: "freezing fog", 51: "light drizzle", 53: "drizzle",
    55: "heavy drizzle", 56: "freezing drizzle", 57: "freezing drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain", 66: "freezing rain",
    67: "freezing rain", 71: "light snow", 73: "snow", 75: "heavy snow",
    77: "snow grains", 80: "rain showers", 81: "rain showers",
    82: "violent rain showers", 85: "snow showers", 86: "heavy snow showers",
    95: "a thunderstorm", 96: "a thunderstorm with hail", 99: "a thunderstorm with hail",
}


@dataclass(frozen=True, slots=True)
class Weather:
    place: str
    description: str
    temperature: float
    feels_like: float
    wind: float
    unit: str = "C"


@dataclass(frozen=True, slots=True)
class Definition:
    word: str
    part_of_speech: str
    meaning: str
    example: str = ""


@dataclass(frozen=True, slots=True)
class Story:
    title: str
    url: str
    score: int


def _get_json(url: str, *, params=None, timeout=10.0, user_agent="MrAjeeb/2.0", label="service"):
    try:
        response = requests.get(
            url, params=params, timeout=timeout, headers={"User-Agent": user_agent}
        )
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as exc:
        status = getattr(exc.response, "status_code", None)
        if status == 404:
            raise NotFound(f"The {label} has no entry for that.") from exc
        log.debug("%s returned %s", label, status)
        raise LookupError_(f"I could not reach the {label} just now.") from exc
    except requests.RequestException as exc:
        log.debug("%s request failed: %s", label, exc)
        raise LookupError_(f"I could not reach the {label} just now.") from exc
    except ValueError as exc:
        raise LookupError_(f"The {label} sent something I could not read.") from exc


def weather(
    place: str, *, timeout: float = 10.0, user_agent: str = "MrAjeeb/2.0", metric: bool = True
) -> Weather:
    """Current conditions for a place, via Open-Meteo (no API key required)."""
    place = place.strip()
    if not place:
        raise LookupError_("Tell me which place you want the weather for.")

    found = _get_json(
        GEOCODE_API,
        params={"name": place, "count": 1, "language": "en", "format": "json"},
        timeout=timeout,
        user_agent=user_agent,
        label="weather service",
    )
    results = found.get("results") or []
    if not results:
        raise LookupError_(f"I could not find a place called {place}.")

    spot = results[0]
    label = ", ".join(filter(None, (spot.get("name"), spot.get("country"))))
    data = _get_json(
        FORECAST_API,
        params={
            "latitude": spot["latitude"],
            "longitude": spot["longitude"],
            "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
            "temperature_unit": "celsius" if metric else "fahrenheit",
            "wind_speed_unit": "kmh" if metric else "mph",
        },
        timeout=timeout,
        user_agent=user_agent,
        label="weather service",
    )
    current = data.get("current") or {}
    if "temperature_2m" not in current:
        raise LookupError_(f"No current readings for {label}.")

    return Weather(
        place=label,
        description=WEATHER_CODES.get(current.get("weather_code"), "hard to describe"),
        temperature=round(float(current["temperature_2m"])),
        feels_like=round(float(current.get("apparent_temperature", current["temperature_2m"]))),
        wind=round(float(current.get("wind_speed_10m", 0))),
        unit="C" if metric else "F",
    )


def define(word: str, *, timeout: float = 10.0, user_agent: str = "MrAjeeb/2.0") -> Definition:
    """First dictionary sense of ``word``.

    Wiktionary is asked first because it is Wikimedia-hosted and dependable;
    dictionaryapi.dev is a free service that returns 502s often enough to need a
    backup rather than a retry.
    """
    word = word.strip()
    if not word:
        raise LookupError_("Tell me which word to define.")

    missing = False
    try:
        return _wiktionary_definition(word, timeout=timeout, user_agent=user_agent)
    except NotFound:
        missing = True
    except LookupError_:
        log.debug("wiktionary unavailable, falling back")

    try:
        return _dictionaryapi_definition(word, timeout=timeout, user_agent=user_agent)
    except NotFound:
        missing = True
    except LookupError_ as exc:
        # Only claim the word does not exist if a dictionary actually said so.
        if not missing:
            raise LookupError_(f"I could not reach a dictionary to look up {word}.") from exc

    raise NotFound(f"I have no definition for {word}.")


def _wiktionary_definition(word: str, *, timeout: float, user_agent: str) -> Definition:
    payload = _get_json(
        WIKTIONARY_API.format(word=quote_plus(word.replace(" ", "_"))),
        timeout=timeout,
        user_agent=user_agent,
        label="dictionary",
    )
    for sense in (payload or {}).get("en", []):
        for meaning in sense.get("definitions", []):
            text = _strip_markup(meaning.get("definition", ""))
            if text:
                examples = [_strip_markup(e) for e in meaning.get("examples", [])]
                return Definition(
                    word=word,
                    part_of_speech=sense.get("partOfSpeech", "").lower(),
                    meaning=text,
                    example=next((e for e in examples if e), ""),
                )
    raise NotFound(f"I have no definition for {word}.")


def _dictionaryapi_definition(word: str, *, timeout: float, user_agent: str) -> Definition:
    payload = _get_json(
        DICTIONARY_API.format(word=quote_plus(word)),
        timeout=timeout,
        user_agent=user_agent,
        label="dictionary",
    )
    for entry in payload if isinstance(payload, list) else []:
        for meaning in entry.get("meanings", []):
            for sense in meaning.get("definitions", []):
                if sense.get("definition"):
                    return Definition(
                        word=entry.get("word", word),
                        part_of_speech=meaning.get("partOfSpeech", ""),
                        meaning=sense["definition"],
                        example=sense.get("example", ""),
                    )
    raise NotFound(f"I have no definition for {word}.")


def top_stories(
    limit: int = 3, *, timeout: float = 10.0, user_agent: str = "MrAjeeb/2.0"
) -> list[Story]:
    """Front page of Hacker News (no key, no scraping)."""
    ids = _get_json(HN_TOP, timeout=timeout, user_agent=user_agent, label="news service")
    stories: list[Story] = []
    for item_id in (ids or [])[: max(1, limit)]:
        item = _get_json(
            HN_ITEM.format(item_id=item_id),
            timeout=timeout,
            user_agent=user_agent,
            label="news service",
        )
        if not item or not item.get("title"):
            continue
        stories.append(
            Story(
                title=item["title"],
                url=item.get("url") or f"https://news.ycombinator.com/item?id={item_id}",
                score=int(item.get("score", 0)),
            )
        )
    if not stories:
        raise LookupError_("The news service had nothing for me.")
    return stories
