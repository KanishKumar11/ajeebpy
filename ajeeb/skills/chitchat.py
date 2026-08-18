"""Small talk: hello, goodbye, who are you, and the jokes."""

from __future__ import annotations

import random
import re
from datetime import datetime

from ajeeb.config import Settings
from ajeeb.registry import Context, Reply, phrase, registry, skill

__all__ = ["greeting"]

_JOKES = (
    "I told my computer I needed a break, and it said: no problem, I will go to sleep.",
    "There are only ten kinds of people: those who read binary and those who do not.",
    "A SQL query walks into a bar, goes up to two tables and asks: may I join you?",
    "I would tell you a UDP joke, but you might not get it.",
    "Debugging: being the detective in a crime movie where you are also the culprit.",
    "My code works and I have no idea why. My code fails and I have no idea why.",
    "A byte walked into a bar looking miserable. The barman asked: parity error?",
)


def greeting(settings: Settings) -> str:
    """Time-appropriate hello, used on startup by every front-end."""
    hour = datetime.now().hour
    if hour < 12:
        part = "Good morning"
    elif hour < 18:
        part = "Good afternoon"
    else:
        part = "Good evening"
    return (
        f"{part}! I am {settings.assistant_name}, created by {settings.creator}. "
        "How can I help you?"
    )


@skill(
    "exit",
    phrase(r"(?:exit|quit|stop|goodbye|good bye|bye|bye bye|shut ?down|go to sleep|see you)"),
    help="End the conversation.",
    examples=("exit", "goodbye"),
    priority=100,
)
def _exit(ctx: Context, _match: re.Match[str]) -> Reply:
    return Reply(f"Goodbye! {ctx.settings.assistant_name} signing off.", stop=True)


@skill(
    "help",
    phrase(r"(?:help|commands|options|what can you do|what do you do|what else can you do)"),
    help="List everything I can do.",
    examples=("help", "what can you do"),
    priority=90,
)
def _help(_ctx: Context, _match: re.Match[str]) -> Reply:
    listed = [entry for entry in registry if entry.help and entry.name != "help"]
    lines = [f"- {entry.help}" for entry in listed]
    display = "Here is what I can do:\n" + "\n".join(lines)
    return Reply(f"I can do about {len(listed)} things. Have a look at the list.", display)


@skill(
    "greeting",
    phrase(
        r"(?:hi+|hello+|hey+|yo|namaste|greetings|good (?:morning|afternoon|evening))"
        r"(?: there| again)?"
    ),
    phrase(r"how are you(?: doing)?|hows it going|whats up|sup"),
    help="Say hello.",
    examples=("hello", "good morning", "how are you"),
    priority=80,
)
def _greeting(ctx: Context, match: re.Match[str]) -> Reply:
    if "how are you" in match.group(0) or "going" in match.group(0) or "up" in match.group(0):
        return Reply(
            random.choice(
                (
                    "Running well, thank you. What can I do for you?",
                    "All circuits nominal. How can I help?",
                    "Never better -- I do not sleep. What do you need?",
                )
            )
        )
    return Reply(greeting(ctx.settings))


@skill(
    "thanks",
    r"\b(?:thanks|thank you|thankyou|thx|shukriya|nandri)\b",
    help="Accept your thanks graciously.",
    examples=("thank you",),
    priority=70,
)
def _thanks(_ctx: Context, _match: re.Match[str]) -> Reply:
    return Reply(random.choice(("That is my pleasure!", "Any time!", "Happy to help!")))


@skill(
    "creator",
    r"\b(?:who (?:made|created|built|wrote|programmed) you|your (?:creator|maker|developer))\b",
    help="Tell you who built me.",
    examples=("who made you",),
    priority=75,
)
def _creator(ctx: Context, _match: re.Match[str]) -> Reply:
    return Reply(f"I was built by {ctx.settings.creator}.")


@skill(
    "name",
    r"\byour name\b",
    phrase(r"who are you|what are you|introduce yourself"),
    help="Tell you my name.",
    examples=("what is your name", "who are you"),
    priority=75,
)
def _name(ctx: Context, _match: re.Match[str]) -> Reply:
    return Reply(f"My name is {ctx.settings.assistant_name}.")


@skill(
    "age",
    r"\b(?:your age|how old are you|when were you (?:born|created|made))\b",
    help="Tell you how old I am.",
    examples=("how old are you",),
    priority=75,
)
def _age(ctx: Context, _match: re.Match[str]) -> Reply:
    born = ctx.settings.born_on.strftime("%d %B %Y")
    return Reply(f"I was created on {born}, which makes me {ctx.settings.age_years} years old.")


@skill(
    "relationship",
    r"\b(?:relationship|girlfriend|boyfriend|married|dating)\b",
    help="Reveal my relationship status.",
    examples=("are you in a relationship",),
    priority=70,
)
def _relationship(_ctx: Context, _match: re.Match[str]) -> Reply:
    return Reply("Yes, I am in a relationship with the Wi-Fi. It is a strong connection.")


@skill(
    "joke",
    phrase(r"(?:tell me |say )?(?:a |another |something )?(?:joke|funny|make me laugh)"),
    r"\b(?:tell|crack|hear|another)\b.{0,12}\bjoke\b",
    r"\b(?:say|tell me) something funny\b",
    help="Tell you a joke.",
    examples=("tell me a joke", "crack a joke"),
    priority=35,
)
def _joke(_ctx: Context, _match: re.Match[str]) -> Reply:
    try:
        import pyjokes  # optional extra
    except ImportError:
        return Reply(random.choice(_JOKES))
    return Reply(pyjokes.get_joke())
