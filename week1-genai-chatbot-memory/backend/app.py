"""
StudyMate Backend (FastAPI)
---------------------------
A stateful AI study-buddy chatbot.

Implements Project 1 requirements:
- Connects to a frontier LLM (Google Gemini) via official SDK + API key
- Maintains an in-memory list/array per session to store conversation history
- Appends every new user input and model response to that history
- Validates input and blocks empty/whitespace-only messages before they
  reach the GenAI API (the "Structural Validation Gate")
"""

import json
import os
import uuid
from datetime import datetime, timezone

import google.generativeai as genai
from dotenv import load_dotenv
from google.api_core.exceptions import ResourceExhausted
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
    )

genai.configure(api_key=API_KEY)

BASE_SYSTEM_PROMPT = (
    "You are StudyMate, a friendly and encouraging study buddy. "
    "You explain concepts simply, ask clarifying questions, and quiz the "
    "user on topics they say they're studying. Keep responses concise and "
    "supportive. Remember details the user shares (their name, the subject "
    "they're studying, what's already been covered) and use that context "
    "in later replies."
)


def build_system_prompt(profile: dict) -> str:
    """Inject known facts about the user into the base prompt so a brand
    new chat session already 'knows' them, without merging conversations."""
    if not profile:
        return BASE_SYSTEM_PROMPT

    facts = []
    if profile.get("name"):
        facts.append(f"The user's name is {profile['name']}.")
    if profile.get("subjects"):
        facts.append(
            "Topics this user has studied before: " + ", ".join(profile["subjects"]) + "."
        )

    if not facts:
        return BASE_SYSTEM_PROMPT

    return (
        BASE_SYSTEM_PROMPT
        + "\n\nKnown context about this returning user (from earlier sessions): "
        + " ".join(facts)
        + " Greet them naturally using this if appropriate, without being repetitive about it."
    )


# Lightweight extractor model used to pull durable facts out of a finished
# turn (name, subjects) without re-sending the whole chat history. Kept
# separate from the main chat model/session so it doesn't pollute history.
extractor_model = genai.GenerativeModel(model_name="gemini-2.5-flash")


def update_user_profile(profile: dict, user_message: str, reply_text: str) -> None:
    """Best-effort extraction of durable facts (name, subject) from a turn.
    Failures here should never break the chat -- profile memory is a nice-to-have."""
    try:
        prompt = (
            "Extract any of the following from this exchange, if present: "
            "the user's name, and any academic/technical subject they say "
            "they are studying or want to learn. "
            'Respond ONLY with compact JSON: {"name": "..." or null, '
            '"subject": "..." or null}. No other text.\n\n'
            f"User: {user_message}\nAssistant: {reply_text}"
        )
        result = extractor_model.generate_content(prompt)
        text = result.text.strip().strip("`").removeprefix("json").strip()
        data = json.loads(text)

        if data.get("name"):
            profile["name"] = data["name"]
        if data.get("subject"):
            profile.setdefault("subjects", [])
            if data["subject"] not in profile["subjects"]:
                profile["subjects"].append(data["subject"])
    except Exception:  # noqa: BLE001
        pass  # profile extraction is non-critical; never break the chat turn


app = FastAPI(title="StudyMate API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store: { session_id: [ {role, parts}, ... ] }
# NOTE: Intentionally simple per the Project 1 spec. It resets whenever the
# server restarts -- that's expected at this stage. Real persistence
# (Postgres/Firestore) is a later-project concern, not v1.
sessions: dict[str, list[dict]] = {}

# Metadata for the chat-history sidebar: { session_id: {created_at, title} }
# "title" is derived from the first user message once one is sent.
session_meta: dict[str, dict] = {}

# A single, server-wide profile of "the user" (this app has no auth/multiple
# accounts -- it's one local user). Carries durable facts (name, subjects)
# across separate topic threads, without merging the threads themselves.
user_profile: dict = {}

# Each session gets its own GenerativeModel instance because the system
# prompt is personalized with the profile snapshot at session-creation time.
session_models: dict[str, genai.GenerativeModel] = {}

MAX_HISTORY_TURNS = 40  # simple FIFO safeguard against unbounded growth


class ChatRequest(BaseModel):
    session_id: str
    message: str

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        # Structural Validation Gate: reject empty / whitespace-only input
        if not v or not v.strip():
            raise ValueError("Message cannot be empty.")
        return v


class ChatResponse(BaseModel):
    reply: str


class SessionResponse(BaseModel):
    session_id: str


def trim_history(history: list[dict]) -> None:
    """Sliding-window pruning: drop oldest turns once history grows large."""
    if len(history) > MAX_HISTORY_TURNS:
        del history[: len(history) - MAX_HISTORY_TURNS]


@app.post("/api/session", response_model=SessionResponse)
def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = []
    session_meta[session_id] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": None,
    }
    session_models[session_id] = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=build_system_prompt(user_profile),
    )
    return {"session_id": session_id}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if req.session_id not in sessions:
        raise HTTPException(status_code=400, detail="Invalid or unknown session_id.")

    history = sessions[req.session_id]
    session_model = session_models.get(req.session_id)
    if session_model is None:
        # Defensive fallback (e.g. session created before this feature existed)
        session_model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=build_system_prompt(user_profile),
        )
        session_models[req.session_id] = session_model

    # First message in the session becomes its sidebar title
    if not history and session_meta.get(req.session_id, {}).get("title") is None:
        preview = req.message.strip()
        session_meta[req.session_id]["title"] = (
            preview if len(preview) <= 48 else preview[:45] + "..."
        )

    # 1. Ingest & Append: add the validated user input to history
    history.append({"role": "user", "parts": [req.message]})

    try:
        # 2. Transmit & Record: send the FULL prior history, then the new message
        chat_session = session_model.start_chat(history=history[:-1])
        response = chat_session.send_message(req.message)
        reply_text = response.text
    except ResourceExhausted:
        history.pop()  # don't leave a dangling user turn with no reply
        raise HTTPException(
            status_code=429,
            detail="StudyMate is getting a lot of requests right now (free-tier "
            "limit reached). Please wait about 30 seconds and try again.",
        )
    except Exception as exc:  # noqa: BLE001
        history.pop()  # don't leave a dangling user turn with no reply
        raise HTTPException(status_code=502, detail=f"Model request failed: {exc}") from exc

    # Append the model's response to preserve context for the next turn
    history.append({"role": "model", "parts": [reply_text]})
    trim_history(history)

    # Best-effort: pull durable facts (name, subject) into the global profile
    # so future NEW sessions are personalized too, without merging this
    # conversation's history into them. Only runs for the first couple of
    # turns in a session -- that's when people usually introduce themselves
    # and say what they're studying, and it keeps API usage down (each
    # extraction is a separate Gemini call, on top of the main reply).
    if len(history) <= 4:  # 2 user turns + 2 model replies
        update_user_profile(user_profile, req.message, reply_text)

    return {"reply": reply_text}


@app.get("/api/history/{session_id}")
def get_history(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"history": sessions[session_id]}


@app.get("/api/sessions")
def list_sessions():
    """Return all known sessions with a preview title, newest first.
    Empty sessions (no messages sent yet) are excluded."""
    items = [
        {
            "session_id": sid,
            "title": meta["title"],
            "created_at": meta["created_at"],
        }
        for sid, meta in session_meta.items()
        if meta["title"] is not None
    ]
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return {"sessions": items}


@app.get("/api/profile")
def get_profile():
    return {"profile": user_profile}


@app.get("/api/health")
def health():
    return {"status": "ok"}