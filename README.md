# Infinity Film Studio

[![CI](https://github.com/srinivasagudi0/infinity-film-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/srinivasagudi0/infinity-film-studio/actions/workflows/ci.yml)

AI-assisted filmmaking suite covering script writing, video edit guidance, and storyboarding. Ships with a FastAPI backend, React (Vite) frontend, Docker build, and CLI/desktop shells. Defaults to file-based persistence and works without an API key (returns friendly fallbacks), but unlocks full AI features when `OPENAI_API_KEY` is provided.

## Features
- Script Copilot chat with session persistence and lightweight memory summarization
- One-shot scene, storyboard frame, and edit suggestions
- Video review endpoint that accepts uploads and returns AI notes (uses ffmpeg metadata when available)
- Web UI (React) plus CLI and Tkinter desktop placeholders
- Docker image that serves the built frontend + API on port 8000
- File-based JSON persistence under `media/` with temp storage in `tmp/`

## Project layout
- `Launcher.py` — entry that wires settings + routes to CLI / desktop / web
- `backend/` — FastAPI app, OpenAI client wrapper, domain controllers, services, tests
- `frontend/` — Vite + React single page shell (served statically when built)
- `ScriptWriter.py`, `VideoEditor.py`, `StoryBoard.py` — lightweight module shims for external embedding
- `docs/` — docs stubs (LICENSE, README, CONTRIBUTING)

## Quick start (native)
1) Create env: `cp .env.example .env` and add `OPENAI_API_KEY=` (Hack Club key recommended).  
2) Install Python deps: `pip install -r requirements.txt`  
3) Install frontend deps: `cd frontend && npm install`  
4) Build frontend: `npm run build` (still in `frontend/`)  
5) Run backend (serves API + built frontend):  
   ```bash
   python Launcher.py --ui web --host 0.0.0.0 --port 8000
   ```  
6) Open http://localhost:8000

## Streamlit deployment (secrets-safe)
- The Streamlit apps in this repo now read API configuration from `st.secrets` automatically (and fall back to local env vars).
- Do not paste API keys into the UI. Add them in Streamlit Cloud under **App settings -> Secrets**.
- Start from `.streamlit/secrets.toml.example` and paste only the keys you need.

## One-click helper
`./start.sh` will create `.env` if missing, attempt Docker first, and otherwise install deps, build the frontend, and launch the web UI on port 8000.

## Docker
```bash
docker build -t infinity-film-studio .
docker run --rm -p 8000:8000 --env-file .env infinity-film-studio
```

## Development
- Frontend dev server: `cd frontend && npm run dev` (set `VITE_API_BASE` if backend not on http://localhost:8000)
- Tests: `pytest -q`
- Make targets: `make install`, `make build-frontend`, `make serve-backend`, `make test`

## API surface (paths relative to backend root, default host 8000)
- `GET /api/health` — status
- `GET /api/config` — environment/config info
- `POST /api/script/suggest` — scene suggestion
- `POST /api/script/chat` — ChatGPT-like script copilot (`session_id`, `message`)
- `POST /api/script/chat/new` — create chat session
- `GET /api/script/chats` — list chat sessions
- `GET /api/script/chat/{session_id}` — fetch chat
- `DELETE /api/script/chat/{session_id}` — delete chat
- `POST /api/video/suggest` — edit suggestion
- `POST /api/video/review` — upload video + optional `question` for AI review
- `POST /api/storyboard/suggest` — storyboard frame suggestion

## Environment
- `OPENAI_API_KEY` — optional; without it, responses are friendly fallbacks
- `OPENAI_BASE_URL` — OpenAI-compatible endpoint (defaults to Hack Club in `.env.example`)
- `OPENAI_DEFAULT_CHAT_MODEL` — default chat model (cost-optimized default: `google/gemini-2.5-flash-lite-preview-09-2025`)
- Provider priority is enforced as `Hack Club -> OpenAI -> Offline`
- `OPENAI_API_KEY_FALLBACK` — optional legacy fallback key
- `OPENAI_BASE_URL_FALLBACK` — optional legacy fallback endpoint
- `OPENAI_MODEL_FALLBACK` — optional legacy fallback chat model override
- `OPENAI_API_KEY_FALLBACK_<N>` — ordered fallback keys (`_1`, `_2`, ...) tried before offline mode
- `OPENAI_BASE_URL_FALLBACK_<N>` — optional endpoint override for fallback slot `<N>`
- `OPENAI_MODEL_FALLBACK_<N>` — optional chat model override for fallback slot `<N>`
- `OPENAI_FALLBACK_OPENAI_MODEL` — OpenAI-safe fallback model used when default model is Gemini-style
- `MEDIA_ROOT` / `TEMP_ROOT` — storage paths (default `./media`, `./tmp`)
- `CORS_ORIGINS` — comma-separated origins (default `*`)
- `LOG_LEVEL` — info/debug/warning/error (default `info`)

Example `Hack Club -> OpenAI -> Offline` setup:
```env
OPENAI_API_KEY=your_hackclub_key
OPENAI_BASE_URL=https://ai.hackclub.com/proxy/v1
OPENAI_DEFAULT_CHAT_MODEL=google/gemini-2.5-flash-lite-preview-09-2025
OPENAI_API_KEY_FALLBACK_1=your_openai_key
OPENAI_BASE_URL_FALLBACK_1=https://api.openai.com/v1
OPENAI_MODEL_FALLBACK_1=gpt-4.1-mini
```

Keep real keys in local `.env` or deployment secret managers only. `.env` is ignored by git in this repo.
For Streamlit Cloud, put the same keys in Secrets instead of committing them.

## Notes
- ffmpeg is installed in the Docker image; locally, installing `ffmpeg` + `ffmpeg-python` enables richer metadata.
- File persistence uses JSON stores under `media/` (scripts, chats, media assets, storyboards).

Enjoy exploring the studio!

## Contributing
See [CONTRIBUTING](CONTRIBUTING.md) for branch workflow, testing, and review expectations. Please use the provided PR template and issue forms.

## Code of Conduct
We adhere to the [Contributor Covenant](CODE_OF_CONDUCT.md). Be kind, be respectful.

## Security
Report vulnerabilities to [security@infinityfilmstudio.com](mailto:security@infinityfilmstudio.com) as outlined in [SECURITY](SECURITY.md). Please avoid filing public issues for security concerns.

## License
MIT — see [LICENSE](LICENSE).


You are free to use, modify, and distribute this software under the terms of the MIT License.

## Acknowledgements
- Built with FastAPI, REACT, OpenAI API
- Inspired by the creativity of Canvas, Figma, and other collaborative tools. 
- Thanks to all future contributors and users for helping shape this project!


PEACE. ✌️
