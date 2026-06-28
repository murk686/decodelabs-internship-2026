# StudyMate — Week 1: GenAI Chatbot with Memory

A stateful AI study-buddy chatbot built for the DecodeLabs internship,
Week 1 / Generative AI track.

## What it does

StudyMate is a conversational web app that remembers what you've told it
during the session — your name, the subject you're studying, what's
already been covered — and uses that context in later replies. This
demonstrates the core skill of the project: turning a stateless LLM API
into a contextual, multi-turn conversation.

## Tech stack

- **Backend:** FastAPI (Python) + Google Gemini API (`gemini-1.5-flash`)
- **Frontend:** React (Vite)

## How it works (the memory mechanism)

1. Each browser session gets a `session_id` from `POST /api/session`.
2. The backend keeps an **in-memory list** of every message exchanged,
   keyed by `session_id`.
3. On each new message, the backend appends the user's input to that
   list, sends the **entire history** to Gemini, then appends the
   model's reply — so the next turn has full context.
4. Empty or whitespace-only messages are rejected before they ever reach
   the Gemini API (the "Structural Validation Gate").
5. If history grows past 40 turns, the oldest turns are dropped
   (sliding-window pruning) to protect against context-window overflow.

History is stored in memory only — it resets if the backend restarts.
That's expected for this stage of the project; persistent storage
(Postgres/Firestore) is a later concern, not part of v1.

## Running it locally

### 1. Get a free Gemini API key
Visit [Google AI Studio](https://aistudio.google.com/app/apikey) and
generate a free API key.

### 2. Backend setup
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then paste your API key into .env
uvicorn app:app --reload --port 5000
```
Backend runs at `http://localhost:5000`. Interactive API docs at
`http://localhost:5000/docs`.

### 3. Frontend setup
```bash
cd frontend
npm install
npm run dev
```
Frontend runs at `http://localhost:5173`.

## Testing the memory ("the memory exam")

1. Open the app and say: *"My name is Vipin."*
2. Ask it to write something long, e.g. *"Write a short poem about technology."*
3. Then ask: *"What's my name?"*

If it correctly answers "Vipin," the stateful memory loop is working.

## Project structure
```
week1-genai-chatbot-memory/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── main.jsx
        ├── App.jsx
        └── index.css
```
