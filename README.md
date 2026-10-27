# AI Multimodal Chatbot

A chatbot with text, image and web-search input. FastAPI backend, vanilla JS frontend, local models via Ollama.

## User Interface
<img width="700" height="400" alt="image" src="https://github.com/user-attachments/assets/887cb746-6464-42f0-8737-c4df6281a941" />


## Features
- Live streaming replies (SSE) with a Stop button
- Image upload (resized in the browser) using a vision model
- Web search with a "searching" status and source links
- Server-side session memory

## Tech stack
Python, FastAPI, Ollama (`llama3.2`, `gemma3:4b`) through the OpenAI-compatible API, HTML, CSS, JavaScript

## How it works
Text messages go to `llama3.2`, which can call a `web_search` tool. Messages with images go to `gemma3:4b`.

```
Browser -> POST /chat -> FastAPI -> Ollama (local)
                                 -> Ollama web search API
        <- SSE stream <-
```

## Structure
```
backend/   main.py, config.py, services/ (llm, search, memory)
frontend/  index.html, style.css, app.js
```

## Setup
```bash
ollama pull llama3.2
ollama pull gemma3:4b

cd backend
pip install fastapi "uvicorn[standard]" openai httpx python-dotenv
```

Create `backend/.env`:
```
OLLAMA_API_KEY=your-key   # only needed for web search
TEXT_MODEL=llama3.2
VISION_MODEL=gemma3:4b
```

## Run
```bash
uvicorn main:app --reload
```
Open `http://localhost:8000` (not the HTML file directly).

## Notes
- Session memory is in RAM, so it resets when the server restarts.
- Images and web search are not used together: a chat with images stays on the vision model.
