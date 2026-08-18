# 🎙️ Mr. Ajeeb

A voice assistant I first wrote in 2020 as a beginner, rebuilt as a small, tested
Python package with two front-ends: a terminal REPL and a Streamlit chat app that
uses your **browser's** microphone.

```
you   > what is the time
ajeeb > The time is 7:20 PM.
you   > who is ada lovelace
ajeeb > According to Wikipedia: Augusta Ada King, Countess of Lovelace, was an
        English mathematician and writer chiefly known for her work on Charles
        Babbage's proposed mechanical general-purpose computer…
```

## Quick start

```bash
git clone https://github.com/keenkanish/ajeebpy
cd ajeebpy
python -m venv .venv && .venv\Scripts\activate     # macOS/Linux: source .venv/bin/activate

# Web UI (recommended - no PyAudio needed)
pip install -e ".[web]"
streamlit run app.py

# Terminal
pip install -e ".[cli]"
python -m ajeeb                 # type at it
python -m ajeeb --voice         # microphone
python -m ajeeb --ask "roll a dice"
```

Only `requests` is required for the core. Everything else is an optional extra,
and the assistant degrades gracefully when a piece is missing: no microphone
means it asks you to type, no speech engine means it prints instead of speaking.

## The two front-ends

| | Terminal (`python -m ajeeb`) | Web (`streamlit run app.py`) |
|---|---|---|
| Microphone | local, via PyAudio | **the browser's**, via `st.audio_input` |
| Voice | offline system voice (pyttsx3) | gTTS audio played in the page |
| Links | opens your browser | rendered as a button |
| Best for | quick local use, scripting | sharing, phones, machines without PyAudio |

## Command-line options

```
python -m ajeeb [--voice] [--ask TEXT] [--no-speak] [--open-links]
                [--list-skills] [--voice-name NAME] [--rate WPM] [-v]
```

Configuration also reads `AJEEB_*` environment variables, so nothing needs
editing in code:

| Variable | Default | Meaning |
|---|---|---|
| `AJEEB_NAME` | `Mr. Ajeeb` | What it calls itself |
| `AJEEB_CREATOR` | `Keen Kanish` | Who it credits |
| `AJEEB_ADDRESS_AS` | *(empty)* | How it addresses you, e.g. `Boss` |
| `AJEEB_SPEAK` | `1` | `0` turns speech off |
| `AJEEB_VOICE` | *(empty)* | Match a system voice by name, e.g. `Zira` |
| `AJEEB_SPEECH_RATE` | `165` | Words per minute |
| `AJEEB_LANGUAGE` | `en-IN` | Recognition + speech language |
| `AJEEB_WIKI_SENTENCES` | `2` | How much Wikipedia to read out |
| `AJEEB_HOME_TOWN` | *(empty)* | Assumed by "what's the weather" with no place |
| `AJEEB_HOME` | `~/.ajeeb` | Where notes are kept |

## What it can do

32 skills. Say `help` at the prompt, or run `python -m ajeeb --list-skills`.

| | |
|---|---|
| **Time** | the time · the date · a calendar for any month · the time in another city · "how many days until christmas" |
| **Knowledge** | Wikipedia summaries · dictionary definitions · Hacker News headlines · web search |
| **Weather** | "what's the weather in chennai", or set `AJEEB_HOME_TOWN` and just ask |
| **Media** | play or search YouTube · open a bookmarked site (or any domain) |
| **Maths** | arithmetic, percentages, roots · unit conversion (length, mass, volume, speed, data, time, temperature) |
| **Notes** | "take a note: buy milk" · "read my notes" · "delete note 1" — saved to disk |
| **Odds and ends** | passwords · coin flip · dice (`roll a d20`) · random numbers · jokes · small talk |

Everything except Wikipedia, weather, definitions, news and YouTube works with no
network at all. No skill needs an API key: weather comes from Open-Meteo,
definitions from Wiktionary (with dictionaryapi.dev as a backup), news from the
Hacker News API.

## Adding a skill

One function, one decorator. Nothing else in the project changes:

```python
# ajeeb/skills.py
@skill(
    "weather",
    r"^(?:what(?:s| is)? the )?weather(?: in (?P<city>.+))?$",
    help="Report the weather.",
    examples=("weather in chennai",),
    priority=40,
)
def _weather(ctx: Context, match: re.Match[str]) -> Reply:
    city = match.group("city") or "here"
    return Reply(f"It is lovely in {city}.")
```

`priority` decides who wins when two skills match the same phrase — that is how
`what is the time` reaches the clock instead of the Wikipedia catch-all.

## Tests

```bash
python -m unittest discover -s tests -t .    # no extra install
pytest                                       # if you have it
```

133 tests, all offline: HTTP is stubbed, so the suite never touches the network.
That includes the ones that matter most — that `evaluate()` refuses
`__import__('os').system(...)`, that a fuzzy match never invents an argument, and
that out-of-scope sentences are declined rather than misrouted.

## How it is put together

```
ajeeb/
  config.py       Settings dataclass, AJEEB_* environment overrides
  registry.py     intent registry: patterns -> handlers, priority, typo tolerance
  skills/
    chitchat.py   hello, goodbye, who are you, jokes
    clock.py      time, date, calendar, world clock, countdowns
    web.py        Wikipedia, weather, definitions, news, search, YouTube
    tools.py      maths, unit conversion, passwords, dice, notes
  services.py     every HTTP call the skills make, in one place
  calc.py         ast-based expression evaluator + unit tables
  storage.py      JSON-backed notes that survive a restart
  tts.py          speech out: pyttsx3 locally, gTTS bytes for the browser
  stt.py          speech in: live mic, or a recorded clip from the browser
  assistant.py    settings + skills + voice, with no UI attached
  cli.py          terminal front-end
app.py            Streamlit front-end
```

The core knows nothing about either UI, which is why both drive the same skills.

## What it is not

It is a **command assistant, not a chatbot**, and it is worth being precise about
where the line falls. Measured against a fixed list of phrasings:

| | |
|---|---|
| Paraphrases of skills it has ("time please", "put on some lofi", "gimme a random number") | **18/18** |
| Requests outside the skill list ("write me an email", "I had a rough day") | **declined, never guessed at** |
| Follow-ups that need memory ("and in Tokyo?", "when did she die") | **0/4 — not supported** |

The first row is what broadening the patterns bought: the same list scored 9/18
before. The last row is the honest limit — every turn is independent, so a
follow-up that only makes sense in the context of the previous answer will not
land. Regexes cannot fix that; it needs a model in the loop.

The middle row is a deliberate choice. The router will say "I did not catch that"
rather than route "I had a rough day" to the nearest-looking skill, because a
confidently wrong answer is worse than an honest miss. The typo-tolerant second
pass is tuned the same way: it will rescue "flip a coion", but it refuses to
guess when acting on the guess would mean inventing an argument you never said.


## What changed from the 2020 version

The original was one 150-line script. The rewrite fixes the things that actually
broke or would have bitten later:

- **Kivy is gone.** It only ever opened a window with a button reading "close
  this to continue", and it ran *before* the assistant started. Streamlit
  replaces it with a real chat UI — and because `st.audio_input` uses the
  browser's microphone, PyAudio is no longer required at all.
- **`voices[2].id` crashed** on any machine with fewer than three installed
  voices. Voices are now looked up by name with a fallback to the default.
- **`except Exception: pass` hid real bugs.** Failures now carry a reason:
  "I did not hear anything", "the speech service is unreachable", and so on.
- **`warnings.filterwarnings('ignore')` is gone** — it silenced the whole process.
- **Dead dependencies dropped.** The `wikipedia` package has not been released
  since 2014, and `pywhatkit` drives YouTube by faking keystrokes. Both are
  replaced by direct HTTPS calls through `requests`.
- **No way out.** The old `while True` had no exit command; `exit`, `bye` and
  Ctrl+C all work now.
- **The `if/elif` ladder became a registry**, so skills are declarative, ordered
  by priority, and testable one at a time.
- **`random` and `calendar` were imported but never used** — now they power the
  coin, dice and calendar skills.
- **Time and date are read out properly.** The old `date()` spoke three bare
  numbers ("18", "8", "2026"); it now says "Tuesday, 18 August 2026", and the
  age is computed rather than hard-coded.
- **Type hints, logging, tests and packaging** throughout: `pyproject.toml`,
  ruff + mypy configuration, an `ajeeb` console script, and 133 offline tests.
- **The `if/elif` ladder could only match exact phrasings.** Politeness and filler
  ("could you tell me what time it is") are now absorbed by one shared helper, so
  each skill describes the *core* of what it answers to instead of spelling out
  every combination.

## Licence

MIT — original assistant by Keen Kanish, 2020; rebuilt 2026.
