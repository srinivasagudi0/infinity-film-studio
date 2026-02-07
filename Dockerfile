# Multistage build: frontend (Node) then backend (Python)

# Frontend build stage
FROM node:20-alpine as frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Backend stage
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system deps (ffmpeg optional; included for completeness)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY Launcher.py README.md ScriptWriter.py StoryBoard.py VideoEditor.py .env.example ./
COPY docs ./docs
COPY frontend/dist ./frontend/dist

# Expose web port
EXPOSE 8000

# Default command: run web UI (serves API + built frontend)
CMD ["python", "Launcher.py", "--ui", "web", "--host", "0.0.0.0", "--port", "8000"]

# Optional: Command to run API only (without frontend)
# CMD ['python', 'Launcher.py', '--api', '--host', '


