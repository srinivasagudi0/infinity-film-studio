# Infinity Film Studio

[![CI](https://github.com/srinivasagudi0/infinity-film-studio/actions/workflows/ci.yml/badge.svg)](https://github.com/srinivasagudi0/infinity-film-studio/actions/workflows/ci.yml)

AI-assisted filmmaking suite covering script writing, video edit guidance, and storyboarding. Ships with a FastAPI backend, React (Vite) frontend, Docker build, and CLI/desktop shells. Defaults to file-based persistence and works without an OpenAI key (returns friendly fallbacks), but unlocks full AI features when `OPENAI_API_KEY` is provided.

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
1) Create env: `cp .env.example .env` and add `OPENAI_API_KEY=` if you have one.  
2) Install Python deps: `pip install -r requirements.txt`  
3) Install frontend deps: `cd frontend && npm install`  
4) Build frontend: `npm run build` (still in `frontend/`)  
5) Run backend (serves API + built frontend):  
   ```bash
   python Launcher.py --ui web --host 0.0.0.0 --port 8000
   ```  
6) Open http://localhost:8000

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
- `OPENAI_BASE_URL` — override OpenAI endpoint if needed
- `MEDIA_ROOT` / `TEMP_ROOT` — storage paths (default `./media`, `./tmp`)
- `CORS_ORIGINS` — comma-separated origins (default `*`)
- `LOG_LEVEL` — info/debug/warning/error (default `info`)

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
