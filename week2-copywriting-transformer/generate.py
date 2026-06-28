"""
Automated Copywriting & Tone Transformer
-----------------------------------------
DecodeLabs Internship 2026 — Project 2

Core concepts demonstrated:
- Dynamic prompt template compilation using Python f-strings
- User-defined variables: Product_Name, Platform, Tone
- Inference parameter tuning: Temperature and Top_P per tone profile
- Platform-specific constraints injected at prompt-compile time
"""

import os
import sys
import argparse
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

# Force UTF-8 output on Windows so emojis in AI-generated copy
# don't crash when printing to terminal or redirecting to a file.
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set. Copy .env.example to .env and add your key.")

genai.configure(api_key=API_KEY)

# ── Platform Profiles ──────────────────────────────────────────────────────────
# Each platform gets specific constraints injected directly into the prompt.
# This is the "Platform-Specific Filtering" concept from the slides.

PLATFORM_PROFILES = {
    "linkedin": {
        "label": "LinkedIn",
        "constraints": (
            "Write a professional LinkedIn post. "
            "Use a strong opening hook, 2-3 short paragraphs, and end with a call to action. "
            "Include 3-5 relevant hashtags at the end. "
            "Maximum 1300 characters. No emojis unless one is used sparingly in the hook."
        ),
    },
    "instagram": {
        "label": "Instagram",
        "constraints": (
            "Write an Instagram caption. "
            "Start with an attention-grabbing first line (this is what shows before 'more'). "
            "Keep it vibrant and visual. Use line breaks for readability. "
            "End with 5-10 relevant hashtags on a new line. "
            "Maximum 2200 characters."
        ),
    },
    "twitter": {
        "label": "Twitter/X",
        "constraints": (
            "Write a tweet. "
            "Hard limit: 280 characters including spaces — this is a strict API constraint. "
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
            "Keep the body under 200 words. Professional but human tone."
        ),
    },
}

# ── Tone Profiles ──────────────────────────────────────────────────────────────
# Temperature controls randomness (0 = deterministic, 1 = very creative).
# Top_P controls diversity of token selection (nucleus sampling).
# These are the inference hyper-parameters the slides focus on.

TONE_PROFILES = {
    "professional": {
        "label": "Professional",
        "description": "authoritative, polished, and trustworthy — like a seasoned expert",
        "temperature": 0.2,   # low: consistent, structured, formal output
        "top_p": 0.8,
    },
    "witty": {
        "label": "Witty",
        "description": "clever, playful, and memorable — with unexpected linguistic hooks",
        "temperature": 0.9,   # high: diverse phrasing, creative surprises
        "top_p": 0.95,
    },
    "casual": {
        "label": "Casual",
        "description": "friendly, conversational, and approachable — like talking to a friend",
        "temperature": 0.6,   # medium: relaxed but not chaotic
        "top_p": 0.9,
    },
    "urgent": {
        "label": "Urgent",
        "description": "action-driven and time-sensitive — creates FOMO and drives immediate action",
        "temperature": 0.3,   # low-medium: clear and direct, minimal meandering
        "top_p": 0.85,
    },
}


def compile_prompt(
    product_name: str,
    description: str,
    platform: str,
    tone: str,
) -> str:
    """
    The Master Instruction Template — compiles user variables into a
    structured prompt using Python f-strings.

    This is the core of Project 2: isolating raw user input from the
    prompt structure, then injecting it safely at compile time.
    """
    platform_profile = PLATFORM_PROFILES[platform]
    tone_profile = TONE_PROFILES[tone]

    # Dynamic f-string template: variables injected, structure fixed
    prompt = f"""You are an expert marketing copywriter specializing in high-converting digital content.

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
Do not include any preamble, explanation, or notes. Output only the final copy, ready to publish.
"""
    return prompt


def generate_copy(
    product_name: str,
    description: str,
    platform: str,
    tone: str,
) -> str:
    """
    Calls the Gemini model with a compiled prompt and tuned inference
    parameters. Returns the generated marketing copy.
    """
    tone_profile = TONE_PROFILES[tone]

    # Compile the dynamic prompt template
    prompt = compile_prompt(product_name, description, platform, tone)

    # Configure the model with tone-specific inference parameters
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config=genai.GenerationConfig(
            temperature=tone_profile["temperature"],
            top_p=tone_profile["top_p"],
            max_output_tokens=600,
        ),
    )

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except ResourceExhausted:
        return (
            "[ERROR] Free-tier quota reached. "
            "Please wait a minute and try again."
        )
    except Exception as exc:  # noqa: BLE001
        return f"[ERROR] Generation failed: {exc}"


def print_result(
    product_name: str,
    platform: str,
    tone: str,
    copy: str,
) -> None:
    """Pretty-prints the generated copy with metadata."""
    platform_label = PLATFORM_PROFILES[platform]["label"]
    tone_label = TONE_PROFILES[tone]["label"]
    temp = TONE_PROFILES[tone]["temperature"]
    top_p = TONE_PROFILES[tone]["top_p"]

    separator = "-" * 60
    print(f"\n{separator}")
    print(f"  Product : {product_name}")
    print(f"  Platform: {platform_label}")
    print(f"  Tone    : {tone_label}  (temp={temp}, top_p={top_p})")
    print(separator)
    print(copy)
    print(separator)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automated Copywriting & Tone Transformer — DecodeLabs Project 2"
    )
    parser.add_argument(
        "--product", "-p",
        required=True,
        help="Product name (e.g. 'AuraFlow Wireless Earbuds')",
    )
    parser.add_argument(
        "--description", "-d",
        required=True,
        help="Short product description (e.g. 'Premium earbuds with 40hr battery')",
    )
    parser.add_argument(
        "--platform",
        choices=list(PLATFORM_PROFILES.keys()),
        default="linkedin",
        help="Target platform: linkedin | instagram | twitter | email (default: linkedin)",
    )
    parser.add_argument(
        "--tone",
        choices=list(TONE_PROFILES.keys()),
        default="professional",
        help="Tone: professional | witty | casual | urgent (default: professional)",
    )
    parser.add_argument(
        "--all-platforms",
        action="store_true",
        help="Generate copy for ALL platforms with the chosen tone",
    )
    parser.add_argument(
        "--all-tones",
        action="store_true",
        help="Generate copy for ALL tones on the chosen platform",
    )

    args = parser.parse_args()

    print(f"\n** Automated Copywriting & Tone Transformer **")
    print(f"   DecodeLabs Internship 2026 - Project 2")

    if args.all_platforms:
        # Generate for every platform with the chosen tone
        for platform in PLATFORM_PROFILES:
            copy = generate_copy(
                args.product, args.description, platform, args.tone
            )
            print_result(args.product, platform, args.tone, copy)

    elif args.all_tones:
        # Generate every tone variant for the chosen platform
        for tone in TONE_PROFILES:
            copy = generate_copy(
                args.product, args.description, args.platform, tone
            )
            print_result(args.product, args.platform, tone, copy)

    else:
        # Single generation
        copy = generate_copy(
            args.product, args.description, args.platform, args.tone
        )
        print_result(args.product, args.platform, args.tone, copy)


if __name__ == "__main__":
    main()