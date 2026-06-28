# CopyForge — Week 2: Automated Copywriting & Tone Transformer

DecodeLabs Internship 2026 — Generative AI Track, Project 2

## What it does

Takes a product name and description, then generates professional
marketing copy tailored to a specific platform and tone — using
dynamic prompt templates and inference parameter tuning.

## Core concepts

- **Dynamic prompt compilation** — Python f-strings inject user variables
  (`Product_Name`, `Platform`, `Tone`) into a structured master template
  at runtime. The user provides raw facts; the code enforces the structure.

- **Inference parameter tuning** — `temperature` and `top_p` are set per
  tone profile, not hardcoded. Witty copy uses `temp=0.9` for creative
  variance; professional copy uses `temp=0.2` for consistent, structured output.

- **Platform-specific constraints** — each platform's character limits and
  format rules are injected directly into the prompt before API transmission
  (e.g. Twitter: 280 chars hard limit; Email: Subject + Preview + CTA structure).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your Gemini API key to .env
```

## Usage

### Single generation
```bash
python generate.py \
  --product "AuraFlow Earbuds" \
  --description "Premium wireless earbuds with 40hr battery and noise cancellation" \
  --platform linkedin \
  --tone professional
```

### Generate for all platforms (same tone)
```bash
python generate.py \
  --product "AuraFlow Earbuds" \
  --description "Premium wireless earbuds with 40hr battery and noise cancellation" \
  --tone witty \
  --all-platforms
```

### Generate all tone variants (same platform)
```bash
python generate.py \
  --product "AuraFlow Earbuds" \
  --description "Premium wireless earbuds with 40hr battery and noise cancellation" \
  --platform instagram \
  --all-tones
```

## Platforms supported
| Platform  | Format | Char limit |
|-----------|--------|------------|
| linkedin  | Post with hashtags | 1300 |
| instagram | Caption with hashtags | 2200 |
| twitter   | Tweet | 280 (strict) |
| email     | Subject + Preview + Body + CTA | ~200 words |

## Tone profiles & inference parameters
| Tone | Temperature | Top_P | Use case |
|------|-------------|-------|----------|
| professional | 0.2 | 0.80 | LinkedIn B2B, formal emails |
| witty | 0.9 | 0.95 | Instagram, social media |
| casual | 0.6 | 0.90 | General audience content |
| urgent | 0.3 | 0.85 | Flash sales, time-sensitive |

## Project structure
```
week2-copywriting-transformer/
├── generate.py        # Main script
├── requirements.txt
├── .env.example
└── README.md
```
