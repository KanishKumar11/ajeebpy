"""Time, date, calendars, world clock and countdowns."""

from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ajeeb.registry import Context, Reply, phrase, skill

# Spoken city names -> IANA zones, so "time in tokyo" does not need "Asia/Tokyo".
CITY_ZONES: dict[str, str] = {
    "utc": "UTC", "gmt": "UTC",
    "london": "Europe/London", "paris": "Europe/Paris", "berlin": "Europe/Berlin",
    "madrid": "Europe/Madrid", "rome": "Europe/Rome", "moscow": "Europe/Moscow",
    "dubai": "Asia/Dubai", "delhi": "Asia/Kolkata", "new delhi": "Asia/Kolkata",
    "mumbai": "Asia/Kolkata", "chennai": "Asia/Kolkata", "bangalore": "Asia/Kolkata",
    "bengaluru": "Asia/Kolkata", "kolkata": "Asia/Kolkata", "india": "Asia/Kolkata",
    "colombo": "Asia/Colombo", "dhaka": "Asia/Dhaka", "karachi": "Asia/Karachi",
    "singapore": "Asia/Singapore", "hong kong": "Asia/Hong_Kong", "beijing": "Asia/Shanghai",
    "shanghai": "Asia/Shanghai", "tokyo": "Asia/Tokyo", "japan": "Asia/Tokyo",
    "seoul": "Asia/Seoul", "sydney": "Australia/Sydney", "melbourne": "Australia/Melbourne",
    "auckland": "Pacific/Auckland", "new york": "America/New_York", "nyc": "America/New_York",
    "boston": "America/New_York", "toronto": "America/Toronto", "chicago": "America/Chicago",
    "denver": "America/Denver", "los angeles": "America/Los_Angeles",
    "la": "America/Los_Angeles", "san francisco": "America/Los_Angeles",
    "seattle": "America/Los_Angeles", "mexico city": "America/Mexico_City",
    "sao paulo": "America/Sao_Paulo", "buenos aires": "America/Argentina/Buenos_Aires",
    "lagos": "Africa/Lagos", "cairo": "Africa/Cairo", "nairobi": "Africa/Nairobi",
    "johannesburg": "Africa/Johannesburg",
}

# Countdown targets that have no fixed date in the calendar module.
HOLIDAYS: dict[str, tuple[int, int]] = {
    "christmas": (12, 25),
    "new year": (1, 1),
    "new years": (1, 1),
    "new years eve": (12, 31),
    "halloween": (10, 31),
    "valentines": (2, 14),
    "valentines day": (2, 14),
}


def _spoken_time(moment: datetime) -> str:
    return moment.strftime("%I:%M %p").lstrip("0")


@skill(
    "time",
    phrase(r"(?:what(?:'?s| is)? )?(?:the )?time(?: is it| now)?"),
    phrase(r"what time (?:is it|it is)"),
    phrase(r"(?:the )?current time"),
    phrase(r"time check"),
    help="Tell you the current time.",
    examples=("what is the time", "what time is it"),
    priority=62,
)
def _time(ctx: Context, _match: re.Match[str]) -> Reply:
    return Reply(ctx.settings.address(f"The time is {_spoken_time(datetime.now())}."))


@skill(
    "world_clock",
    phrase(r"(?:what(?:'?s| is)? )?(?:the )?time (?:in|at) (?P<place>.+?)"),
    phrase(r"what time is it in (?P<place>.+?)"),
    help="Tell you the time somewhere else, e.g. 'time in tokyo'.",
    examples=("what time is it in tokyo", "time in london"),
    priority=70,
)
def _world_clock(_ctx: Context, match: re.Match[str]) -> Reply:
    place = match.group("place").strip().lower().strip("?.")
    zone_name = CITY_ZONES.get(place, place.replace(" ", "_").title() if "/" in place else None)
    if zone_name is None:
        known = ", ".join(sorted({"tokyo", "london", "new york", "dubai", "sydney", "delhi"}))
        return Reply(f"I do not know the timezone for {place}. Try one of: {known}.")
    try:
        zone = ZoneInfo(zone_name)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return Reply(f"I do not know the timezone for {place}.")

    there = datetime.now(zone)
    difference = (there.utcoffset() or timedelta()) - (
        datetime.now().astimezone().utcoffset() or timedelta()
    )
    hours = difference.total_seconds() / 3600
    if hours == 0:
        gap = "the same as here"
    else:
        gap = f"{abs(hours):.0f} hours {'ahead of' if hours > 0 else 'behind'} you".replace(
            "1 hours", "1 hour"
        )
    return Reply(
        f"It is {_spoken_time(there)} in {place.title()}, {gap}.",
        f"{place.title()} ({zone_name}) — {there.strftime('%A %d %B, %I:%M %p')}",
    )


@skill(
    "date",
    phrase(r"(?:what(?:'?s| is)? )?(?:the |today'?s )?date"),
    phrase(r"what day is (?:it|today)"),
    phrase(r"(?:what(?:'?s| is)? )?(?:the )?day today"),
    phrase(r"what is today"),
    help="Tell you the date today.",
    examples=("what is the date", "what day is it"),
    priority=62,
)
def _date(ctx: Context, _match: re.Match[str]) -> Reply:
    spoken = datetime.now().strftime("%A, %d %B %Y").replace(" 0", " ")
    return Reply(ctx.settings.address(f"Today is {spoken}."))


@skill(
    "calendar",
    phrase(r"(?:show (?:me )?(?:the )?)?calendar(?: for (?P<month>[a-z]+))?(?: (?P<year>\d{4}))?"),
    help="Show a calendar for a month, for example 'calendar for March'.",
    examples=("show calendar", "calendar for march"),
    priority=40,
)
def _calendar(_ctx: Context, match: re.Match[str]) -> Reply:
    now = datetime.now()
    year = int(match.group("year") or now.year)
    month_name = (match.group("month") or "").strip()
    month = now.month
    if month_name:
        names = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
        names.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})
        if month_name not in names:
            return Reply(f"I do not know a month called {month_name}.")
        month = names[month_name]
    label = f"{calendar.month_name[month]} {year}"
    return Reply(f"Here is the calendar for {label}.", calendar.month(year, month))


@skill(
    "countdown",
    phrase(r"how (?:many days|long) (?:until|till|to) (?P<target>.+?)"),
    phrase(r"days (?:until|till|to) (?P<target>.+?)"),
    help="Count the days to a date, e.g. 'how many days until christmas'.",
    examples=("how many days until christmas", "days until 2027-01-01"),
    priority=68,
)
def _countdown(_ctx: Context, match: re.Match[str]) -> Reply:
    target = match.group("target").strip().lower().strip("?.")
    today = date.today()

    when: date | None = None
    key = target.removeprefix("the ").replace("'", "")
    if key in HOLIDAYS:
        month, day = HOLIDAYS[key]
        when = date(today.year, month, day)
        if when < today:
            when = date(today.year + 1, month, day)
    else:
        for fmt in ("%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y", "%d/%m/%Y"):
            try:
                when = datetime.strptime(target, fmt).date()
                break
            except ValueError:
                continue

    if when is None:
        return Reply(
            f"I could not work out when {target} is. "
            "Try a date like 2027-01-01, or a holiday like christmas."
        )

    days = (when - today).days
    label = when.strftime("%d %B %Y").lstrip("0")
    if days == 0:
        return Reply(f"{target.title()} is today!")
    if days < 0:
        return Reply(f"{label} was {abs(days)} days ago.")
    return Reply(f"{days} days until {target.title()}, which falls on a {when:%A} ({label}).")
