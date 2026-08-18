"""Mr. Ajeeb on the web -- ``streamlit run app.py``.

This replaces the old Kivy window, which was only ever a button saying "close me
to continue". Streamlit gives a real chat UI, and ``st.audio_input`` borrows the
*browser's* microphone, so PyAudio (the hardest dependency to install on
Windows) is not needed at all.

Speech is deliberately played in the browser through gTTS rather than spoken by
the machine running the server: with a web app, the listener and the server are
not always the same computer.
"""

from __future__ import annotations

import hashlib

import streamlit as st

from ajeeb import Assistant, Settings, __version__
from ajeeb.registry import Reply
from ajeeb.skills import registry
from ajeeb.stt import transcribe
from ajeeb.tts import to_mp3

st.set_page_config(page_title="Mr. Ajeeb", page_icon="🎙️", layout="centered")


@st.cache_data(show_spinner=False, max_entries=64)
def _speech(text: str, language: str) -> bytes | None:
    """Cached so re-runs never re-synthesise the same sentence."""
    return to_mp3(text, language=language)


def _assistant() -> Assistant:
    if "assistant" not in st.session_state:
        settings = Settings.from_env()
        settings.speak_replies = False  # the browser does the talking, not the server
        st.session_state.assistant = Assistant(settings)
        st.session_state.messages = []
    return st.session_state.assistant


def _remember(role: str, text: str, url: str | None = None) -> dict:
    message = {"role": role, "text": text, "url": url}
    st.session_state.messages.append(message)
    return message


def _render(message: dict, *, voice: bool, language: str) -> None:
    is_user = message["role"] == "user"
    # Only the reply produced this run should start playing by itself; popping the
    # flag stops an old answer replaying every time a sidebar widget is touched.
    fresh = message.pop("fresh", False)
    avatar = "🧑" if is_user else "🎙️"
    with st.chat_message("user" if is_user else "assistant", avatar=avatar):
        st.markdown(message["text"])
        if message.get("url"):
            st.link_button("Open link ↗", message["url"])
        if voice and not is_user and message.get("speech"):
            audio = _speech(message["speech"], language)
            if audio:
                st.audio(audio, format="audio/mp3", autoplay=fresh)


def _answer(assistant: Assistant, query: str) -> Reply:
    reply = assistant.ask(query, speak=False)
    message = _remember("assistant", reply.text, reply.url)
    message["speech"] = reply.speech
    message["fresh"] = True
    return reply


assistant = _assistant()
settings = assistant.settings

# ---------------------------------------------------------------- sidebar -- #
with st.sidebar:
    st.title("🎙️ Mr. Ajeeb")
    st.caption(f"v{__version__} · built by {settings.creator}")

    voice_on = st.toggle("Speak the replies", value=True, help="Plays audio in your browser")
    settings.language = st.selectbox(
        "Speech language",
        ("en-IN", "en-US", "en-GB", "hi-IN"),
        index=("en-IN", "en-US", "en-GB", "hi-IN").index(settings.language)
        if settings.language in ("en-IN", "en-US", "en-GB", "hi-IN")
        else 0,
        help="Used for both recognising and speaking",
    )
    settings.wikipedia_sentences = st.slider(
        "Wikipedia sentences", 1, 6, settings.wikipedia_sentences
    )

    st.divider()
    with st.expander(f"What I can do ({len(registry)} skills)"):
        for entry in registry:
            if entry.help:
                example = entry.examples[0] if entry.examples else ""
                st.markdown(f"**{entry.name}** — {entry.help}")
                if example:
                    st.caption(f"try: “{example}”")

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        assistant.context.history.clear()
        st.rerun()

# ------------------------------------------------------------------ chat -- #
if not st.session_state.messages:
    greeting = assistant.greet(speak=False)
    message = _remember("assistant", greeting)
    message["speech"] = greeting

for message in st.session_state.messages:
    _render(message, voice=voice_on, language=settings.language)

# ----------------------------------------------------------------- input -- #
spoken = st.audio_input("🎤 Or record a question instead of typing")
typed = st.chat_input("Ask me something…")

query: str | None = None

if spoken is not None:
    raw = spoken.getvalue()
    fingerprint = hashlib.sha1(raw).hexdigest()
    if fingerprint != st.session_state.get("last_clip"):
        st.session_state.last_clip = fingerprint
        with st.spinner("Listening…"):
            heard = transcribe(raw, settings)
        if heard:
            query = heard.text
        else:
            st.warning(heard.error or "I could not make that out.")

if typed:
    query = typed

if query:
    _remember("user", query)
    with st.spinner("Thinking…"):
        _answer(assistant, query)
    st.rerun()
