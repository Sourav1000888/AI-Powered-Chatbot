import base64
import binascii
import json
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi import Path as PathParam
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

from llm import stream_chat
from services.memory import (
    add_exchange,
    clear_session,
    get_display_history,
    get_history,
)

import asyncio
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="AI Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500", "http://127.0.0.1:8000"],  
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_ID_PATTERN = r"^[A-Za-z0-9-]{8,64}$"
MAX_IMAGES_PER_MESSAGE = 3
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB (decoded)


class ImageIn(BaseModel):
    media_type: Literal["image/jpeg", "image/png", "image/gif", "image/webp"]
    data: str  # base64

    @field_validator("data")
    @classmethod
    def check_data(cls, v: str) -> str:
        if len(v) > MAX_IMAGE_BYTES * 4 // 3 + 4:
            raise ValueError("Image size is bigger than 5 MB")
        try:
            base64.b64decode(v, validate=True)
        except (binascii.Error, ValueError):
            raise ValueError("Image base64 is wrong")
        return v


class ChatRequest(BaseModel):
    session_id: str = Field(pattern=SESSION_ID_PATTERN)
    message: str = Field(default="", max_length=8000)
    images: list[ImageIn] = Field(default_factory=list, max_length=MAX_IMAGES_PER_MESSAGE)

    @model_validator(mode="after")
    def need_something(self):
        if not self.message.strip() and not self.images:
            raise ValueError("At least one messaage or image required")
        return self


def build_user_content(req: ChatRequest) -> list[dict]:
    blocks = [
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:{img.media_type};base64,{img.data}"
            }
        }
        for img in req.images
    ]
    text = req.message.strip()
    if text:
        blocks.append({"type": "text", "text": text})  # image ke baad text
    return blocks


def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(req: ChatRequest):
    user_content = build_user_content(req)
    messages = get_history(req.session_id) + [{"role": "user", "content": user_content}]

    async def event_stream():
        reply = ""
        try:
            async for event in stream_chat(messages):
                if "text" in event:
                    reply += event["text"]
                yield sse(event)
            if not reply.strip():
                raise ValueError("model response empty")
            add_exchange(req.session_id, user_content, reply)  # only save on success
            yield sse({"done": True})

        except asyncio.CancelledError:
            if reply.strip():
                add_exchange(req.session_id, user_content, reply)
            raise
            
        except Exception as e:
            print("CHAT ERROR:", repr(e))
            yield sse({"error": f"{type(e).__name__}: {e}"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/history/{session_id}")
async def history(session_id: str = PathParam(pattern=SESSION_ID_PATTERN)):
    return {"messages": get_display_history(session_id)}


@app.delete("/session/{session_id}")
async def delete_session(session_id: str = PathParam(pattern=SESSION_ID_PATTERN)):
    clear_session(session_id)
    return {"status": "cleared"}


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "Frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="Frontend") 