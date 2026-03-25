# 🎬 Infinity Film Studio

An AI-powered filmmaking tool that helps with scripts, editing ideas, and storyboards.Built with FastAPI + React + Streamlit, and powered by OpenAI.

## 🧠 What It Does

- Helps you write scripts using AI chat
- Gives scene ideas, storyboard frames, and edit suggestions
- Lets you upload videos and get feedback
- Keeps your projects saved with history
- Works across web UI, CLI, and basic desktop setup

## ⚙️ Features
- 💬 Script Copilot (chat with memory)
- 🎥 Scene + storyboard suggestions
- ✂️ Video edit recommendations
- 📊 Rough-cut analyzer (timestamps + export options)
- 💾 Save/load projects with version history
- 📤 Export to Markdown, PDF, CSV, etc.
- 🌐 Web UI + CLI + desktop support
- 🐳 Docker support for easy setup

## 🗂️ Project Structure
- backend/ → FastAPI + AI logic
- frontend/ → React (Vite) UI
- Launcher.py → main entry point
- docs/ → documentation
- Extra modules for scripts, video, storyboard

## ⚡ Quick Start
```
pip install -r requirements.txt

export OPENAI_API_KEY == "sk-your-key-here"

streamlit run streamlit_run.py
```

## 🔐 Setup
Required:

OPENAI_API_KEY=your_key

Optional:
- model selection
- storage paths
- logging level

## ▶️ Run Modes
- CLI → simple usage
- Web UI → full experience
- Streamlit → analysis tools

## 🧠 API (basic)
- /api/script/chat → script assistant
- /api/video/review → video feedback
- /api/storyboard/suggest → storyboard ideas

## 📦 Storage
- Uses JSON files in media/
- Temp files in tmp/
- Saves scripts, chats, and assets

## ⚠️ Notes
- Needs OpenAI key to run fully
- Works with ffmpeg for better video analysis
- Without AI → limited functionality

## 📜 License
MIT License — free to use and modify

## 🙌 Credits
- FastAPI
- React
* OpenAI
Inspired by tools like Figma and creative platforms.

## 🏁 Final
Still improving.More features coming.

PEACE ✌️


