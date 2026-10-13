import asyncio
import json

from langchain_core.messages import AIMessage, AIMessageChunk

from reflect.auth import create_jwt, decode_jwt, hash_password, verify_password
from reflect.service import (
    _content_to_text,
    _normalize_reflection_source,
    _normalize_thread_id,
    stream_chat,
)


def test_password_hash_roundtrip() -> None:
    password = "correct horse battery staple"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)


def test_jwt_roundtrip() -> None:
    user_id = "app_user:test-user"
    token = create_jwt(user_id)

    assert decode_jwt(token) == user_id


def test_reflection_source_aliases() -> None:
    assert _normalize_reflection_source(None) == "app"
    assert _normalize_reflection_source("telegram") == "telegram_text"
    assert _normalize_reflection_source("telegram-voice") == "voice"
    assert _normalize_reflection_source("voice note") == "voice"
    assert _normalize_reflection_source("unknown-source") == "app"


def test_thread_id_normalization() -> None:
    assert _normalize_thread_id("chat-session-abc", "chat-session") == "chat-session-abc"

    generated = _normalize_thread_id(None, "chat-session")
    assert generated.startswith("chat-session-")
    assert len(generated) > len("chat-session-")


def test_content_to_text_flattens_message_content() -> None:
    assert _content_to_text("plain answer") == "plain answer"
    assert _content_to_text(["a", "b"]) == "ab"
    assert (
        _content_to_text(
            [
                {"type": "text", "text": "Let me look. "},
                {"type": "tool_use", "id": "toolu_123", "name": "get_graph_summary", "input": {}},
                {"type": "text", "text": "Done."},
            ]
        )
        == "Let me look. Done."
    )
    assert _content_to_text(None) == "None"
    assert _content_to_text([{"type": "text_delta", "text": "Hello"}]) == "Hello"


class _ScriptedChatAgent:
    def __init__(self, events: list[dict]) -> None:
        self._events = events

    async def astream_events(self, *_args, **_kwargs):
        for event in self._events:
            yield event


def _sse_payloads(chunks: list[str]) -> list[dict]:
    payloads = []
    for chunk in chunks:
        for line in chunk.splitlines():
            if line.startswith("data: "):
                payloads.append(json.loads(line[6:]))
    return payloads


async def _collect_chat(events: list[dict], monkeypatch) -> list[dict]:
    monkeypatch.setattr(
        "reflect.service._build_chat_agent_for_user",
        lambda _user_id: _ScriptedChatAgent(events),
    )
    chunks = [chunk async for chunk in stream_chat("What patterns keep showing up?", "chat-1", "app_user:demo")]
    return _sse_payloads(chunks)


def test_stream_chat_uses_final_message_when_chunks_have_no_text(monkeypatch) -> None:
    events = [
        {
            "event": "on_chat_model_stream",
            "data": {
                "chunk": AIMessageChunk(
                    content=[{"type": "tool_use", "id": "call_1", "name": "get_graph_summary", "input": {}}]
                )
            },
        },
        {
            "event": "on_chat_model_end",
            "data": {"output": AIMessage(content="People-pleasing shows up most often when you feel anxious.")},
        },
    ]

    payloads = asyncio.run(_collect_chat(events, monkeypatch))
    tokens = [item["content"] for item in payloads if item["type"] == "token"]

    assert tokens == ["People-pleasing shows up most often when you feel anxious."]
    assert not any(item["type"] == "error" for item in payloads)


def test_stream_chat_does_not_repeat_text_already_streamed(monkeypatch) -> None:
    events = [
        {
            "event": "on_chat_model_stream",
            "data": {"chunk": AIMessageChunk(content=[{"type": "text", "text": "You often "}] )},
        },
        {
            "event": "on_chat_model_stream",
            "data": {"chunk": AIMessageChunk(content=[{"type": "text_delta", "text": "people-please."}] )},
        },
        {
            "event": "on_chat_model_end",
            "data": {"output": AIMessage(content="You often people-please.")},
        },
    ]

    payloads = asyncio.run(_collect_chat(events, monkeypatch))
    tokens = [item["content"] for item in payloads if item["type"] == "token"]

    assert "".join(tokens) == "You often people-please."
