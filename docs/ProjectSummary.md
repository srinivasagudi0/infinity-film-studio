# Infinity Film Studio — Project Summary (1 page)

## Problem
Filmmakers juggle disconnected tools for script drafts, storyboards, and video review. That fragmentation slows iteration, scatters context, and makes it hard to reproduce creative decisions across a team—or for a solo creator working with cloud APIs that may be unavailable.

## Architecture
- **Stack**: FastAPI backend + React (Vite) frontend, with CLI/desktop entry via `Launcher.py`.
- **AI layer**: OpenAI client with deterministic fallbacks when no API key is set; prompt registry governs tone and guardrails.
- **Domain modules**: Script copilot chat, storyboard frame synthesis, and video review endpoints; JSON persistence under `media/` plus `tmp/` for uploads.
- **Delivery**: Docker image serving built frontend + API on port 8000; native runs via `python Launcher.py --ui web` after installing Python/Node deps.

## Challenges
- Balancing offline determinism with richer model-powered outputs when credentials are available.
- Maintaining coherent narrative context across chat sessions and storyboard frames without overlong prompts.
- Handling video review gracefully when ffmpeg metadata is missing or uploads are partial.
- Keeping the stack simple enough for contributors while covering web, CLI, and desktop entry points.

## What I Learned
- Designing prompt programs as versioned assets is key for reproducibility and evaluation.
- Deterministic fallbacks (no-key mode) make demos and tests reliable, while still offering a path to stronger generations with OpenAI.
- Clear JSON schemas and fixtures under `media/` speed up testing and onboarding.
- Shipping a single entry point (`Launcher.py`) keeps UX consistent across shells (web/CLI/desktop).

---
**Use cases**: Suitable as concise application text, email context to introduce the project, and a portfolio backbone summary.
**Contact**: srinivasagudi0@gmail.com
