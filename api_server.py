from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from reflect.auth import (
    confirm_password_reset,
    demo_login,
    get_current_user,
    login_user,
    register_user,
    request_password_reset,
)
from reflect.db import get_connection, init_schema
from reflect.service import (
    daily_prompt,
    get_dashboard_payload,
    get_people_overview_payload,
    get_reflections,
    run_chat,
    run_reflection_pipeline,
    stream_chat,
    stream_reflection_pipeline,
)


APP_NAME = "synapse-api"
logger = logging.getLogger(__name__)

app = FastAPI(title="Synapse API", version="0.3.0")
limiter = Limiter(key_func=get_remote_address, storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"))
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def internal_error_handler(request: Request, exc: Exception):
    logger.error("Unhandled request failure", exc_info=(type(exc), exc, exc.__traceback__))
    return JSONResponse(status_code=500, content={"detail": "Internal error"})


@app.on_event("startup")
def startup_init_schema():
    conn = get_connection()
    init_schema(conn)

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

# Shared DB connection for auth routes (lightweight, no ML init)
def get_db():
    return get_connection()


# ── Auth request/response models ──

class RegisterRequest(BaseModel):
    email: str = Field(description="User email address")
    password: str = Field(min_length=8, description="Password (min 8 chars)")


class LoginRequest(BaseModel):
    email: str
    password: str


class ResetRequestBody(BaseModel):
    email: str


class ResetConfirmBody(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class AuthResponse(BaseModel):
    user_id: str
    email: str
    token: str


class ResetRequestResponse(BaseModel):
    message: str


# ── Data request/response models ──

class ReflectionRequest(BaseModel):
    reflection_text: str = Field(min_length=1)
    daily_prompt: str | None = Field(default=None)
    thread_id: str | None = Field(default=None)
    source: str | None = Field(default="app")


class ReflectionResponse(BaseModel):
    thread_id: str
    result: dict[str, Any]


class AskRequest(BaseModel):
    message: str = Field(min_length=1)
    thread_id: str | None = Field(default=None)


class AskResponse(BaseModel):
    thread_id: str
    answer: str
    messages: list[dict[str, str]]


class ReflectionSource(BaseModel):
    id: str
    text: str
    daily_prompt: str | None = None
    source: str | None = None
    created_at: Any | None = None


# ── Health ──

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": APP_NAME}


# ── Auth routes ──

@app.post("/api/auth/register", response_model=AuthResponse)
@limiter.limit("5/hour")
def register(request: Request, payload: RegisterRequest):
    try:
        conn = get_db()
        return register_user(conn, payload.email, payload.password)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal error") from exc


@app.post("/api/auth/login", response_model=AuthResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest):
    try:
        conn = get_db()
        return login_user(conn, payload.email, payload.password)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal error") from exc


@app.post("/api/auth/demo-login", response_model=AuthResponse)
@limiter.limit("30/minute")
def demo_login_route(request: Request):
    try:
        conn = get_db()
        return demo_login(conn)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal error") from exc


@app.post("/api/auth/reset-request", response_model=ResetRequestResponse)
@limiter.limit("3/hour")
def reset_request(request: Request, payload: ResetRequestBody, background_tasks: BackgroundTasks):
    # Always acknowledge before account lookup or email delivery, including failures.
    background_tasks.add_task(deliver_password_reset, payload.email)
    return ResetRequestResponse(
        message="If that email exists, password reset instructions have been sent.",
    )


def deliver_password_reset(email: str) -> None:
    conn = None
    try:
        conn = get_db()
        request_password_reset(conn, email)
    except Exception:
        logger.exception("Password reset delivery failed")
    finally:
        if conn is not None:
            conn.close()


@app.post("/api/auth/reset-confirm")
@limiter.limit("10/minute")
def reset_confirm(request: Request, payload: ResetConfirmBody):
    try:
        conn = get_db()
        confirm_password_reset(conn, payload.token, payload.new_password)
        return {"message": "Password updated successfully."}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal error") from exc


# ── Protected data routes ──

@app.get("/api/daily-prompt")
def get_prompt(user_id: str = Depends(get_current_user)) -> dict[str, str]:
    return {"prompt": daily_prompt()}


@app.post("/api/reflection", response_model=ReflectionResponse)
def submit_reflection(
    payload: ReflectionRequest,
    user_id: str = Depends(get_current_user),
) -> ReflectionResponse:
    try:
        graph_result = run_reflection_pipeline(
            reflection_text=payload.reflection_text,
            daily_prompt=payload.daily_prompt,
            thread_id=payload.thread_id,
            source=payload.source,
            user_id=user_id,
        )
        return ReflectionResponse.model_validate(graph_result)
    except Exception as exc:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal error") from exc


@app.post("/api/reflection/stream")
async def submit_reflection_stream(
    payload: ReflectionRequest,
    user_id: str = Depends(get_current_user),
) -> StreamingResponse:
    return StreamingResponse(
        stream_reflection_pipeline(
            reflection_text=payload.reflection_text,
            daily_prompt=payload.daily_prompt,
            thread_id=payload.thread_id,
            source=payload.source,
            user_id=user_id,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/chat", response_model=AskResponse)
def ask_graph(
    payload: AskRequest,
    user_id: str = Depends(get_current_user),
) -> AskResponse:
    try:
        raw = run_chat(message=payload.message, thread_id=payload.thread_id, user_id=user_id)
        messages = [m for m in raw.get("messages", []) if m.get("role") in ("ai", "assistant")]
        latest = next((m["content"] for m in reversed(messages)), "")
        if not latest:
            latest = raw.get("messages", [{}])[-1].get("content", "")
        return AskResponse(thread_id=raw["thread_id"], answer=latest, messages=raw["messages"])
    except Exception as exc:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal error") from exc


@app.post("/api/chat/stream")
async def ask_graph_stream(
    payload: AskRequest,
    user_id: str = Depends(get_current_user),
) -> StreamingResponse:
    return StreamingResponse(
        stream_chat(message=payload.message, thread_id=payload.thread_id, user_id=user_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/dashboard")
def dashboard(
    limit: int = Query(default=8, ge=1, le=20),
    user_id: str = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        payload = get_dashboard_payload(user_id=user_id)
        if limit != 8:
            trimmed = {}
            for key, value in payload.items():
                if isinstance(value, list):
                    trimmed[key] = value[:limit]
                elif isinstance(value, dict):
                    trimmed[key] = {k: (v[:limit] if isinstance(v, list) else v) for k, v in value.items()}
                else:
                    trimmed[key] = value
            return trimmed
        return payload
    except Exception as exc:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal error") from exc


@app.get("/api/people")
def people_overview(user_id: str = Depends(get_current_user)) -> dict[str, Any]:
    try:
        return get_people_overview_payload(user_id=user_id)
    except Exception as exc:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal error") from exc


@app.get("/api/reflections", response_model=list[ReflectionSource])
def reflections(user_id: str = Depends(get_current_user)) -> list[ReflectionSource]:
    try:
        return [ReflectionSource.model_validate(r) for r in get_reflections(user_id=user_id)]
    except Exception as exc:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal error") from exc
