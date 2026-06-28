# DecodeLabs Internship 2026 — Generative AI Track

A portfolio of AI engineering projects built during my internship at **DecodeLabs**, a govt. registered enterprise.

## Projects

### Week 1 — StudyMate: AI Chatbot with Memory
> **Core concept:** Stateful conversation architecture — transforming a stateless LLM into a contextual, multi-turn study buddy.

- Persistent session memory across browser refreshes
- Cross-session user profile (remembers your name and subjects between topics)
- Chat history sidebar with multiple saved conversations
- Markdown rendering, dark mode, export chat
- **Stack:** FastAPI · React · Google Gemini API

### Week 2 — CopyForge: Automated Copywriting & Tone Transformer
> **Core concept:** Dynamic prompt template compilation and inference parameter tuning to control AI creative output.

- Dynamic f-string prompt templates injecting Product, Platform, and Tone variables
- Inference parameter tuning — Temperature and Top_P per tone profile
- Platform-specific constraints (LinkedIn, Instagram, Twitter/X, Email)
- CLI script + full web app UI
- Regenerate, download, and session history features
- **Stack:** FastAPI · React · Google Gemini API · Python CLI (argparse)

## Tech Stack
- **Backend:** Python, FastAPI, Google Gemini API (`gemini-2.5-flash`)
- **Frontend:** React, Vite
- **Tools:** Git, VS Code

## Setup
Each project has its own `README.md` with full setup instructions. Both require a free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

## Author
**Murk Sikandar** — Python & GenAI Developer  
Internship Batch: 2026 | Powered by DecodeLabs
