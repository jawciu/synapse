from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from .agent import build_reflection_graph, _init
from .chat_agent import build_chat_agent
from .prompts import get_daily_prompt


_reflection_graph = None
_chat_agent = None


@dataclass(slots=True)
class ChatMessage:
    role: str
    content: str


def _normalize_thread_id(thread_id: str | None, prefix: str) -> str:
    return thread_id or f"{prefix}-{uuid.uuid4()}"


def _ensure_graph():
    global _reflection_graph
    if _reflection_graph is None:
        _reflection_graph = build_reflection_graph()
    return _reflection_graph


def _ensure_chat():
    global _chat_agent
    if _chat_agent is None:
        _chat_agent = build_chat_agent()
    return _chat_agent


def run_reflection_pipeline(reflection_text: str, daily_prompt: str | None, thread_id: str | None) -> dict[str, Any]:
    graph = _ensure_graph()
    _init()

    active_thread = _normalize_thread_id(thread_id, "reflection-session")
    result = graph.invoke(
        {
            "reflection_text": reflection_text,
            "daily_prompt": daily_prompt,
            "messages": [],
        },
        config={"configurable": {"thread_id": active_thread}},
    )
    return {
        "thread_id": active_thread,
        "result": result,
    }


def run_chat(message: str, thread_id: str | None) -> dict[str, Any]:
    chat_agent = _ensure_chat()
    _init()
    active_thread = _normalize_thread_id(thread_id, "chat-session")
    response = chat_agent.invoke(
        {"messages": [HumanMessage(content=message)]},
        config={"configurable": {"thread_id": active_thread}},
    )
    messages = []
    for msg in response["messages"]:
        if isinstance(msg, (HumanMessage, AIMessage)) or hasattr(msg, "type"):
            messages.append(
                ChatMessage(
                    role=getattr(msg, "type", "assistant"),
                    content=getattr(msg, "content", str(msg)),
                )
            )
        elif isinstance(msg, dict):
            messages.append(
                ChatMessage(
                    role=msg.get("type", "assistant"),
                    content=str(msg.get("content", "")),
                )
            )
        else:
            messages.append(ChatMessage(role="assistant", content=str(msg)))

    return {
        "thread_id": active_thread,
        "messages": [message.__dict__ for message in messages],
    }


def get_dashboard_payload() -> dict[str, Any]:
    _init()
    from .agent import _conn

    if _conn is None:
        return {
            "patterns_by_category": {"cognitive": [], "emotional": [], "relational": [], "behavioral": []},
            "ifs_parts": [],
            "schemas": [],
            "emotions": [],
            "people": [],
            "body_signals": [],
            "summary": {
                "total_reflections": 0,
                "total_patterns": 0,
                "total_emotions": 0,
                "total_themes": 0,
                "total_people": 0,
                "total_body_signals": 0,
                "top_patterns": [],
                "top_co_occurrences": [],
            },
        }

    # Pull the same shapes as the old Streamlit dashboard so the new frontend
    # can render equivalent views.
    pattern_rows = _conn.query("SELECT name, category, occurrences FROM pattern ORDER BY occurrences DESC")
    if not pattern_rows or isinstance(pattern_rows, str):
        pattern_rows = []

    ifs_rows = _conn.query("SELECT name, role, description, occurrences FROM ifs_part ORDER BY occurrences DESC")
    ifs_rows = [] if (not ifs_rows or isinstance(ifs_rows, str)) else ifs_rows

    schema_rows = _conn.query("SELECT name, domain, coping_style, description, occurrences FROM schema_pattern ORDER BY occurrences DESC")
    schema_rows = [] if (not schema_rows or isinstance(schema_rows, str)) else schema_rows

    emotion_rows = _conn.query("SELECT name, valence, intensity FROM emotion ORDER BY intensity DESC")
    emotion_rows = [] if (not emotion_rows or isinstance(emotion_rows, str)) else emotion_rows

    people_rows = _conn.query("SELECT name, relationship, description, occurrences FROM person ORDER BY occurrences DESC")
    people_rows = [] if (not people_rows or isinstance(people_rows, str)) else people_rows

    body_rows = _conn.query("SELECT name, location, occurrences FROM body_signal ORDER BY occurrences DESC")
    body_rows = [] if (not body_rows or isinstance(body_rows, str)) else body_rows

    co_occurrences = _conn.query("SELECT in.name AS pattern_a, out.name AS pattern_b, count AS times FROM co_occurs_with ORDER BY times DESC LIMIT 10")
    if co_occurrences is None or isinstance(co_occurrences, str):
        co_occurrences = []

    reflections_total = _conn.query("SELECT count() AS total FROM reflection GROUP ALL")
    total_reflections = reflections_total[0]["total"] if reflections_total and not isinstance(reflections_total, str) else 0

    themes_rows = _conn.query("SELECT name FROM theme") or []
    total_patterns = len(pattern_rows)
    total_emotions = len(emotion_rows)
    total_themes = len(themes_rows)
    total_people = len(people_rows)
    total_body_signals = len(body_rows)

    by_category = {"cognitive": [], "emotional": [], "relational": [], "behavioral": []}
    for pattern in pattern_rows:
        category = str(pattern.get("category", "unknown")).strip().lower()
        if category in by_category:
            by_category[category].append(pattern)

    return {
        "patterns_by_category": by_category,
        "ifs_parts": ifs_rows,
        "schemas": schema_rows,
        "emotions": emotion_rows,
        "people": people_rows,
        "body_signals": body_rows,
        "summary": {
            "total_reflections": total_reflections,
            "total_patterns": total_patterns,
            "total_emotions": total_emotions,
            "total_themes": total_themes,
            "total_people": total_people,
            "total_body_signals": total_body_signals,
            "top_patterns": pattern_rows[:5],
            "top_co_occurrences": co_occurrences,
        },
    }


def daily_prompt() -> str:
    return get_daily_prompt()
