"""Anything that reaches the network: knowledge, search, media, weather, news."""

from __future__ import annotations

import re
from urllib.parse import quote_plus

from ajeeb.registry import Context, Reply, phrase, skill
from ajeeb.services import (
    LookupError_,
    define,
    resolve_youtube_video,
    sentences,
    top_stories,
    weather,
    wikipedia_summary,
    youtube_search_url,
)

__all__ = ["SITES"]

SITES: dict[str, str] = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "mail": "https://mail.google.com",
    "github": "https://github.com",
    "maps": "https://maps.google.com",
    "google maps": "https://maps.google.com",
    "wikipedia": "https://www.wikipedia.org",
    "claude": "https://claude.ai",
    "chatgpt": "https://chatgpt.com",
    "stack overflow": "https://stackoverflow.com",
    "stackoverflow": "https://stackoverflow.com",
    "hacker news": "https://news.ycombinator.com",
    "reddit": "https://www.reddit.com",
    "whatsapp": "https://web.whatsapp.com",
    "spotify": "https://open.spotify.com",
    "netflix": "https://www.netflix.com",
    "instagram": "https://www.instagram.com",
    "linkedin": "https://www.linkedin.com",
    "twitter": "https://twitter.com",
    "amazon": "https://www.amazon.in",
    "drive": "https://drive.google.com",
    "calendar": "https://calendar.google.com",
}

_OPENERS = r"(?:open|launch|start|go to|take me to|bring up|visit|browse|fire up)"
_PLAYERS = r"(?:play|put on|listen to|start playing)"


def _search_url(query: str) -> str:
    return f"https://duckduckgo.com/?q={quote_plus(query.strip())}"


@skill(
    "wikipedia",
    phrase(r"(?:search |look up |read )?wikipedia(?: for| about| on)? (?P<topic>.+?)"),
    phrase(r"(?:look up |search (?:for )?|read (?:about )?)?(?P<topic>.+?) (?:on|in) wikipedia"),
    phrase(r"(?:tell me )?about (?P<topic>.+?)"),
    phrase(r"explain (?P<topic>.+?)(?: to me)?"),
    phrase(r"(?:who|what) (?:is|was|are|were) (?P<topic>.+?)"),
    help="Read out a Wikipedia summary, for example 'wikipedia black holes'.",
    examples=("wikipedia python programming", "who is ada lovelace"),
    priority=50,
)
def _wikipedia(ctx: Context, match: re.Match[str]) -> Reply:
    topic = match.group("topic").strip()
    try:
        article = wikipedia_summary(
            topic, timeout=ctx.settings.request_timeout, user_agent=ctx.settings.user_agent
        )
    except LookupError_ as exc:
        return Reply(str(exc))

    short = sentences(article.extract, ctx.settings.wikipedia_sentences)
    return Reply(
        f"According to Wikipedia: {short}",
        f"**{article.title}**\n\n{article.extract}",
        url=article.url,
    )


@skill(
    "weather",
    phrase(r"(?:what(?:'?s| is)? )?(?:the )?weather(?: like)?(?: (?:in|at|for) (?P<place>.+?))?"),
    phrase(r"how(?:'?s| is|s) (?:it|the weather)(?: (?:in|at) (?P<place>.+?))?"),
    phrase(r"is it (?:hot|cold|raining|sunny)(?: (?:in|at) (?P<place>.+?))?"),
    help="Report the weather, for example 'weather in chennai'.",
    examples=("weather in chennai", "what is the weather like"),
    priority=72,
)
def _weather(ctx: Context, match: re.Match[str]) -> Reply:
    place = (match.groupdict().get("place") or ctx.settings.home_town).strip()
    if not place:
        return Reply(
            "Which place? Say 'weather in chennai', or set AJEEB_HOME_TOWN so I can assume one."
        )
    try:
        report = weather(
            place, timeout=ctx.settings.request_timeout, user_agent=ctx.settings.user_agent
        )
    except LookupError_ as exc:
        return Reply(str(exc))

    return Reply(
        f"It is {report.temperature} degrees and {report.description} in {report.place}, "
        f"feels like {report.feels_like}, wind {report.wind} kilometres per hour.",
        f"**{report.place}** — {report.description}, {report.temperature}°{report.unit} "
        f"(feels like {report.feels_like}°{report.unit}), wind {report.wind} km/h",
    )


@skill(
    "definition",
    phrase(r"(?:what does )?(?P<word>[a-z'-]+) mean"),
    phrase(r"(?:define|definition of|meaning of|what is the meaning of) (?P<word>[a-z' -]+?)"),
    help="Define a word, for example 'define serendipity'.",
    examples=("define serendipity", "what does recursion mean"),
    priority=74,
)
def _definition(ctx: Context, match: re.Match[str]) -> Reply:
    word = match.group("word").strip()
    try:
        found = define(
            word, timeout=ctx.settings.request_timeout, user_agent=ctx.settings.user_agent
        )
    except LookupError_ as exc:
        return Reply(str(exc))

    part = f" ({found.part_of_speech})" if found.part_of_speech else ""
    display = f"**{found.word}**{part}\n\n{found.meaning}"
    if found.example:
        display += f"\n\n*{found.example}*"
    return Reply(f"{found.word}{part}: {found.meaning}", display)


@skill(
    "news",
    phrase(r"(?:what(?:'?s| is)? )?(?:the )?(?:news|headlines|top stories|hacker news)"),
    phrase(r"(?:read|tell|show) me (?:the )?(?:news|headlines)"),
    help="Read the top Hacker News headlines.",
    examples=("what is the news", "read me the headlines"),
    priority=66,
)
def _news(ctx: Context, _match: re.Match[str]) -> Reply:
    try:
        stories = top_stories(
            3, timeout=ctx.settings.request_timeout, user_agent=ctx.settings.user_agent
        )
    except LookupError_ as exc:
        return Reply(str(exc))

    spoken = " ... ".join(f"{index}. {story.title}" for index, story in enumerate(stories, 1))
    display = "\n".join(
        f"{index}. [{story.title}]({story.url}) — {story.score} points"
        for index, story in enumerate(stories, 1)
    )
    return Reply(f"Top of Hacker News right now: {spoken}", display)


@skill(
    "youtube_search",
    phrase(r"(?:search|find|look up) (?:for )?(?P<query>.+?) on youtube"),
    phrase(r"(?:search|find) youtube for (?P<query>.+?)"),
    help="Search YouTube without playing anything.",
    examples=("search youtube for guitar lessons",),
    priority=65,
)
def _youtube_search(_ctx: Context, match: re.Match[str]) -> Reply:
    query = match.group("query").strip()
    return Reply(f"Searching YouTube for {query}.", url=youtube_search_url(query))


@skill(
    "play",
    phrase(rf"{_PLAYERS} (?:some |the |a )?(?P<query>.+?)(?: (?:on|in) youtube)?"),
    help="Play something on YouTube, for example 'play lofi beats'.",
    examples=("play shape of you", "put on some lofi"),
    priority=60,
)
def _play(ctx: Context, match: re.Match[str]) -> Reply:
    query = match.group("query").strip()
    try:
        url = resolve_youtube_video(
            query, timeout=ctx.settings.request_timeout, user_agent=ctx.settings.user_agent
        )
    except LookupError_ as exc:
        return Reply(str(exc))
    return Reply(f"Playing {query} on YouTube.", url=url)


@skill(
    "open_site",
    phrase(rf"{_OPENERS} (?P<site>.+?)"),
    help="Open a website, for example 'open github'.",
    examples=("open youtube", "take me to github"),
    priority=55,
)
def _open_site(_ctx: Context, match: re.Match[str]) -> Reply:
    site = match.group("site").strip().rstrip(".")
    if site in SITES:
        return Reply(f"Opening {site}.", url=SITES[site])
    if "." in site and " " not in site:
        return Reply(f"Opening {site}.", url=f"https://{site}")
    return Reply(
        f"I have no bookmark for {site}, so here is a search instead.", url=_search_url(site)
    )


@skill(
    "search",
    phrase(r"(?:search|google|look up|find)(?: for)? (?P<query>.+?)(?: (?:on|in) (?:the )?web)?"),
    help="Search the web, for example 'search best pizza near me'.",
    examples=("search python tutorials", "google weather today"),
    priority=45,
)
def _search(_ctx: Context, match: re.Match[str]) -> Reply:
    query = match.group("query").strip()
    return Reply(f"Searching the web for {query}.", url=_search_url(query))
