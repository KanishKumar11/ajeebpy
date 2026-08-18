"""Offline utilities: dice, maths, conversions, passwords and notes."""

from __future__ import annotations

import random
import re
import secrets
import string

from ajeeb.calc import CalcError, convert, describe_units, evaluate
from ajeeb.registry import Context, Reply, phrase, skill
from ajeeb.storage import NoteBook

_PUNCTUATION = "!@#$%^&*?-_+="


def _tidy(value: float) -> str:
    """Numbers people can read: 36 rather than 36.0, 14.29 rather than 14.2857..."""
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        rounded = round(value, 4)
        return f"{rounded:,.4f}".rstrip("0").rstrip(".")
    return f"{value:,}"


@skill(
    "coin",
    phrase(r"(?:flip|toss|throw)(?: a| the)? coin"),
    phrase(r"heads or tails"),
    help="Flip a coin.",
    examples=("flip a coin",),
    priority=35,
)
def _coin(_ctx: Context, _match: re.Match[str]) -> Reply:
    return Reply(f"It is {random.choice(('heads', 'tails'))}.")


@skill(
    "dice",
    phrase(r"(?:roll|throw)(?: a| the| some)? (?:dice|die|d(?P<sides>\d+))"
           r"(?: with (?P<faces>\d+) sides)?"),
    help="Roll a dice, e.g. 'roll a d20'.",
    examples=("roll a dice", "roll a d20"),
    priority=35,
)
def _dice(_ctx: Context, match: re.Match[str]) -> Reply:
    groups = match.groupdict()
    sides = max(2, min(int(groups.get("sides") or groups.get("faces") or 6), 1000))
    return Reply(f"You rolled a {random.randint(1, sides)}.")


@skill(
    "random_number",
    phrase(r"(?:give me |pick )?a? ?random number(?: between (?P<low>-?\d+) and (?P<high>-?\d+))?"),
    r"\brandom number between (?P<low>-?\d+) and (?P<high>-?\d+)\b",
    help="Pick a random number.",
    examples=("random number between 1 and 100",),
    priority=35,
)
def _random_number(_ctx: Context, match: re.Match[str]) -> Reply:
    low = int(match.groupdict().get("low") or 1)
    high = int(match.groupdict().get("high") or 100)
    if low > high:
        low, high = high, low
    return Reply(f"I picked {random.randint(low, high)}.")


@skill(
    "convert",
    phrase(r"(?:convert |how many .+ (?:is|in) )?(?P<value>-?\d+(?:\.\d+)?)\s*"
           r"(?P<source>[a-z°/ ]+?) (?:to|in|into) (?P<target>[a-z°/ ]+?)"),
    help="Convert units, e.g. 'convert 10 km to miles'.",
    examples=("convert 10 km to miles", "convert 100 f to c"),
    priority=76,
)
def _convert(_ctx: Context, match: re.Match[str]) -> Reply:
    value = float(match.group("value"))
    source, target = match.group("source").strip(), match.group("target").strip()
    try:
        result, spoken_unit = convert(value, source, target)
    except CalcError as exc:
        return Reply(str(exc))
    return Reply(f"{_tidy(value)} {source} is {_tidy(result)} {spoken_unit}.")


@skill(
    "math",
    phrase(r"(?:what(?:'?s| is)|calculate|compute|work out|solve) (?P<sum>[-+*/^%()\d\s.,]+"
           r"(?:[-+*/^%()\d\s.,a-z]*\d)?)"),
    phrase(r"(?P<sum>\d[\d\s.,]*(?:[-+*/^%]|plus|minus|times|divided by|over)"
           r"[\d\s.,+\-*/^%a-z()]*\d)"),
    phrase(r"(?P<sum>(?:square|cube) root of [\d\s.,]+)"),
    phrase(r"(?P<sum>[\d.,]+\s*(?:%|percent) of [\d\s.,]+)"),
    help="Do arithmetic, e.g. 'what is 15% of 240'.",
    examples=("what is 15% of 240", "12 times 8"),
    priority=78,
)
def _math(_ctx: Context, match: re.Match[str]) -> Reply:
    expression = match.group("sum").strip()
    try:
        answer = evaluate(expression)
    except CalcError as exc:
        return Reply(str(exc))
    return Reply(f"{expression} is {_tidy(answer)}.")


@skill(
    "units_help",
    phrase(r"(?:what|which) units(?: do you know| can you convert)?"),
    help="List the units I can convert between.",
    examples=("what units do you know",),
    priority=77,
)
def _units_help(_ctx: Context, _match: re.Match[str]) -> Reply:
    return Reply("I can convert length, mass, volume, speed, data, time and temperature.",
                 describe_units())


@skill(
    "password",
    phrase(r"(?:generate|make|create|give me)? ?a? ?(?:random |strong |secure )?password"
           r"(?: of| with)? ?(?P<length>\d+)?(?: characters| chars)?"),
    help="Generate a strong password.",
    examples=("generate a password", "make a password with 24 characters"),
    priority=79,
)
def _password(_ctx: Context, match: re.Match[str]) -> Reply:
    length = max(8, min(int(match.groupdict().get("length") or 16), 128))
    alphabet = string.ascii_letters + string.digits + _PUNCTUATION
    # secrets, not random: this one has to be unguessable.
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in candidate)
            and any(c.isupper() for c in candidate)
            and any(c.isdigit() for c in candidate)
            and any(c in _PUNCTUATION for c in candidate)
        ):
            break
    return Reply(
        f"Here is a {length} character password. It is on the screen rather than read aloud.",
        f"`{candidate}`",
    )


# --------------------------------------------------------------------------- #
# Notes -- the one thing here that outlives the conversation
# --------------------------------------------------------------------------- #


def _notebook(ctx: Context) -> NoteBook:
    """One notebook per assistant, created lazily and cached on the context."""
    book = ctx.state.get("notebook")
    if book is None:
        book = NoteBook(ctx.settings.notes_path)
        ctx.state["notebook"] = book
    return book


@skill(
    "note_add",
    phrase(r"(?:take|make|write|add|jot down|save)(?: a| this)? note(?: that| saying| about)?"
           r"[:,]? (?P<text>.+?)"),
    phrase(r"(?:remember|note) that (?P<text>.+?)"),
    phrase(r"remind me (?:to |about )?(?P<text>.+?)"),
    help="Save a note, e.g. 'take a note: buy milk'.",
    examples=("take a note buy milk", "remember that the wifi password is swordfish"),
    priority=85,
)
def _note_add(ctx: Context, match: re.Match[str]) -> Reply:
    text = match.group("text").strip()
    if not text:
        return Reply("What should I write down?")
    note = _notebook(ctx).add(text)
    return Reply(f"Noted: {note.text}")


@skill(
    "note_list",
    phrase(r"(?:read|show|list|what are)(?: me)?(?: my| the)? notes"),
    phrase(r"(?:my|the) notes"),
    phrase(r"what did i (?:note|write down|ask you to remember)"),
    help="Read back your notes.",
    examples=("read my notes", "list my notes"),
    priority=86,
)
def _note_list(ctx: Context, _match: re.Match[str]) -> Reply:
    notes = _notebook(ctx).all()
    if not notes:
        return Reply("Your notebook is empty.")

    spoken = "; ".join(f"{index}. {note.text}" for index, note in enumerate(notes, 1))
    display = "\n".join(f"{index}. {note.text}  _({note.when})_"
                        for index, note in enumerate(notes, 1))
    plural = "note" if len(notes) == 1 else "notes"
    return Reply(f"You have {len(notes)} {plural}: {spoken}", display)


@skill(
    "note_delete",
    phrase(r"(?:delete|remove|forget)(?: my| the)? note (?:number )?(?P<index>\d+)"),
    phrase(r"(?:clear|delete|forget)(?: all)?(?: my| the)? notes"),
    help="Delete one note or clear them all.",
    examples=("delete note 1", "clear my notes"),
    priority=87,
)
def _note_delete(ctx: Context, match: re.Match[str]) -> Reply:
    book = _notebook(ctx)
    index = match.groupdict().get("index")
    if index is None:
        removed = book.clear()
        if not removed:
            return Reply("There was nothing to clear.")
        return Reply(f"Cleared {removed} {'note' if removed == 1 else 'notes'}.")

    try:
        note = book.remove(int(index))
    except IndexError:
        return Reply(f"There is no note number {index}.")
    return Reply(f"Deleted: {note.text}")
