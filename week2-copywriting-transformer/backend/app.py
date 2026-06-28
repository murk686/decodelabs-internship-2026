"""
CopyForge Web Backend (FastAPI)
--------------------------------
Wraps the core generate.py logic into a REST API
for the React frontend to consume.
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set. Copy .env.example to .env and add your key.")

genai.configure(api_key=API_KEY)

# ── Platform Profiles ──────────────────────────────────────────────────────────

PLATFORM_PROFILES = {
    "linkedin": {
        "label": "LinkedIn",
        "constraints": (
            "Write a professional LinkedIn post. "
            "Use a strong opening hook, 2-3 short paragraphs, and end with a call to action. "
            "Include 3-5 relevant hashtags at the end. "
            "Maximum 1300 characters."
        ),
    },
    "instagram": {
        "label": "Instagram",
        "constraints": (
            "Write an Instagram caption. "
            "Start with an attention-grabbing first line. "
            "Keep it vibrant and visual. Use line breaks for readability. "
            "End with 5-10 relevant hashtags on a new line. "
            "Maximum 2200 characters."
        ),
    },
    "twitter": {
        "label": "Twitter/X",
        "constraints": (
            "Write a tweet. "
            "Hard limit: 280 characters including spaces. "
            "Make every word count. Be punchy and direct. "
            "You may use 1-2 hashtags only if they fit within the character limit."
        ),
    },
    "email": {
        "label": "Email",
        "constraints": (
            "Write a marketing email. "
            "Include: Subject line (max 60 chars, label it 'Subject:'), "
            "Preview text (max 90 chars, label it 'Preview:'), "
            "and the email body with a clear CTA button label at the end (label it 'CTA:'). "
            "Keep the body under 200 words."
        ),
    },
}

# ── Tone Profiles ──────────────────────────────────────────────────────────────

TONE_PROFILES = {
    "professional": {
        "label": "Professional",
        "description": "authoritative, polished, and trustworthy",
        "temperature": 0.2,
        "top_p": 0.8,
    },
    "witty": {
        "label": "Witty",
        "description": "clever, playful, and memorable with unexpected hooks",
        "temperature": 0.9,
        "top_p": 0.95,
    },
    "casual": {
        "label": "Casual",
        "description": "friendly, conversational, and approachable",
        "temperature": 0.6,
        "top_p": 0.9,
    },
    "urgent": {
        "label": "Urgent",
        "description": "action-driven and time-sensitive, creates FOMO",
        "temperature": 0.3,
        "top_p": 0.85,
    },
}


def compile_prompt(product_name: str, description: str, platform: str, tone: str) -> str:
    platform_profile = PLATFORM_PROFILES[platform]
    tone_profile = TONE_PROFILES[tone]

    return f"""You are an expert marketing copywriter specializing in high-converting digital content.

PRODUCT INFORMATION:
- Product Name: {product_name}
- Description: {description}

TARGET PLATFORM: {platform_profile["label"]}
TONE: {tone_profile["label"]} — {tone_profile["description"]}

PLATFORM REQUIREMENTS:
{platform_profile["constraints"]}

INSTRUCTIONS:
Generate marketing copy for the product above following the platform requirements exactly.
Match the tone precisely — {tone_profile["description"]}.
Keep the copy concise and complete — never cut off mid-sentence.
Do not include any preamble, explanation, or notes. Output only the final copy, ready to publish.
"""


# ── FastAPI App ────────────────────────────────────────────────────────────────

app = FastAPI(title="CopyForge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    product_name: str
    description: str
    platform: str
    tone: str

    @field_validator("product_name", "description")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty.")
        return v.strip()

    @field_validator("platform")
    @classmethod
    def valid_platform(cls, v: str) -> str:
        if v not in PLATFORM_PROFILES:
            raise ValueError(f"Platform must be one of: {list(PLATFORM_PROFILES.keys())}")
        return v

    @field_validator("tone")
    @classmethod
    def valid_tone(cls, v: str) -> str:
        if v not in TONE_PROFILES:
            raise ValueError(f"Tone must be one of: {list(TONE_PROFILES.keys())}")
        return v


class GenerateResponse(BaseModel):
    copy: str
    platform_label: str
    tone_label: str
    temperature: float
    top_p: float


@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    tone_profile = TONE_PROFILES[req.tone]
    platform_profile = PLATFORM_PROFILES[req.platform]

    prompt = compile_prompt(
        req.product_name, req.description, req.platform, req.tone
    )

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config=genai.GenerationConfig(
            temperature=tone_profile["temperature"],
            top_p=tone_profile["top_p"],
            max_output_tokens=2000,
        ),
    )

    try:
        response = model.generate_content(prompt)
        return GenerateResponse(
            copy=response.text.strip(),
            platform_label=platform_profile["label"],
            tone_label=tone_profile["label"],
            temperature=tone_profile["temperature"],
            top_p=tone_profile["top_p"],
        )
    except ResourceExhausted:
        raise HTTPException(
            status_code=429,
            detail="Free-tier quota reached. Please wait about 30 seconds and try again.",
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Generation failed: {exc}") from exc


@app.get("/api/platforms")
def get_platforms():
    return {
        k: {"label": v["label"]} for k, v in PLATFORM_PROFILES.items()
    }


@app.get("/api/tones")
def get_tones():
    return {
        k: {
            "label": v["label"],
            "description": v["description"],
            "temperature": v["temperature"],
            "top_p": v["top_p"],
        }
        for k, v in TONE_PROFILES.items()
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}