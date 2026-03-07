from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from reflect.service import (
    daily_prompt,
    get_dashboard_payload,
    run_chat,
    run_reflection_pipeline,
    stream_chat,
)


APP_NAME = "synapse-api"

app = FastAPI(title="Synapse API", version="0.2.0")


allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]
if not allowed_origins:
    allowed_origins = ["http://localhost:5173"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReflectionRequest(BaseModel):
    reflection_text: str = Field(min_length=1, description="Raw reflection text")
    daily_prompt: str | None = Field(default=None, description="Optional prompt shown to user")
    thread_id: str | None = Field(default=None, description="Optional custom thread id for persistence")


class ReflectionResponse(BaseModel):
    thread_id: str
    result: dict[str, Any]


class AskRequest(BaseModel):
    message: str = Field(min_length=1, description="Question or prompt for the graph assistant")
    thread_id: str | None = Field(default=None, description="Conversation id for assistant memory")


class AskResponse(BaseModel):
    thread_id: str
    answer: str
    messages: list[dict[str, str]]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": APP_NAME}


@app.get("/api/daily-prompt")
def get_prompt() -> dict[str, str]:
    return {"prompt": daily_prompt()}


@app.post("/api/reflection", response_model=ReflectionResponse)
def submit_reflection(payload: ReflectionRequest) -> ReflectionResponse:
    try:
        graph_result = run_reflection_pipeline(
            reflection_text=payload.reflection_text,
            daily_prompt=payload.daily_prompt,
            thread_id=payload.thread_id,
        )
        return ReflectionResponse.model_validate(graph_result)
    except Exception as exc:  # pragma: no cover - surfaced through API transport
        raise HTTPException(status_code=500, detail=f"Failed to process reflection: {exc}") from exc


@app.post("/api/chat", response_model=AskResponse)
def ask_graph(payload: AskRequest) -> AskResponse:
    try:
        raw = run_chat(message=payload.message, thread_id=payload.thread_id)
        messages = [message for message in raw.get("messages", []) if message.get("role") == "ai" or message.get("role") == "assistant"]
        latest = next((m["content"] for m in reversed(messages)), "")
        if not latest:
            latest = raw.get("messages", [{}])[-1].get("content", "")
        return AskResponse(thread_id=raw["thread_id"], answer=latest, messages=raw["messages"])
    except Exception as exc:  # pragma: no cover - surfaced through API transport
        raise HTTPException(status_code=500, detail=f"Failed to run assistant: {exc}") from exc


@app.post("/api/chat/stream")
async def ask_graph_stream(payload: AskRequest) -> StreamingResponse:
    return StreamingResponse(
        stream_chat(message=payload.message, thread_id=payload.thread_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/dashboard")
def dashboard(limit: int = Query(default=8, ge=1, le=20)) -> dict[str, Any]:
    try:
        payload = get_dashboard_payload()
        if limit != 8:
            # Keep response shape stable with optional truncation support.
            trimmed = {}
            for key, value in payload.items():
                if isinstance(value, list):
                    trimmed[key] = value[:limit]
                elif isinstance(value, dict):
                    trimmed[key] = {
                        k: (v[:limit] if isinstance(v, list) else v)
                        for k, v in value.items()
                    }
                else:
                    trimmed[key] = value
            return trimmed
        return payload
    except Exception as exc:  # pragma: no cover - surfaced through API transport
        raise HTTPException(status_code=500, detail=f"Failed to load dashboard: {exc}") from exc
