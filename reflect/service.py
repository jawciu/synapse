from __future__ import annotations

import json
import uuid
from collections import defaultdict
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from .agent import build_reflection_graph, _init, get_conn_and_vector_store
from .chat_agent import build_chat_agent
from .graph_store import make_graph_tools
from .prompts import get_daily_prompt


_reflection_graph = None

_VALID_REFLECTION_SOURCES = {"app", "telegram_text", "voice"}


@dataclass(slots=True)
class ChatMessage:
    role: str
    content: str


def _normalize_thread_id(thread_id: str | None, prefix: str) -> str:
    return thread_id or f"{prefix}-{uuid.uuid4()}"


def _normalize_reflection_source(source: str | None) -> str:
    if not source:
        return "app"
    normalized = source.strip().lower().replace("-", "_").replace(" ", "_")
    alias_map = {
        "telegram": "telegram_text",
        "telegram_text": "telegram_text",
        "telegramtext": "telegram_text",
        "telegram_voice": "voice",
        "telegramvoice": "voice",
        "voice_note": "voice",
        "voice": "voice",
        "app": "app",
    }
    mapped = alias_map.get(normalized, normalized)
    if mapped in _VALID_REFLECTION_SOURCES:
        return mapped
    return "app"


def _ensure_graph():
    global _reflection_graph
    if _reflection_graph is None:
        _reflection_graph = build_reflection_graph()
    return _reflection_graph


def _build_chat_agent_for_user(user_id: str | None):
    _init()
    conn, vector_store = get_conn_and_vector_store()
    _, chat_tools = make_graph_tools(conn, vector_store, user_id=user_id)
    return build_chat_agent(chat_tools)


def run_reflection_pipeline(
    reflection_text: str,
    daily_prompt: str | None,
    thread_id: str | None,
    source: str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    graph = _ensure_graph()
    _init()

    active_thread = _normalize_thread_id(thread_id, "reflection-session")
    active_source = _normalize_reflection_source(source)
    result = graph.invoke(
        {
            "reflection_text": reflection_text,
            "daily_prompt": daily_prompt,
            "source": active_source,
            "user_id": user_id,
            "messages": [],
        },
        config={"configurable": {"thread_id": active_thread}},
    )
    return {
        "thread_id": active_thread,
        "result": result,
    }


def run_chat(message: str, thread_id: str | None, user_id: str | None = None) -> dict[str, Any]:
    _init()
    active_thread = _normalize_thread_id(thread_id, "chat-session")
    chat_agent = _build_chat_agent_for_user(user_id)
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


async def stream_chat(message: str, thread_id: str | None, user_id: str | None = None) -> AsyncGenerator[str, None]:
    """Yield SSE events as the chat agent streams its response."""
    _init()
    active_thread = _normalize_thread_id(thread_id, "chat-session")
    chat_agent = _build_chat_agent_for_user(user_id)

    yield f"data: {json.dumps({'type': 'thread_id', 'content': active_thread})}\n\n"

    async for event in chat_agent.astream_events(
        {"messages": [HumanMessage(content=message)]},
        config={"configurable": {"thread_id": active_thread}},
        version="v2",
    ):
        kind = event["event"]
        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            token = chunk.content
            if token and isinstance(token, str):
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

    yield f"data: {json.dumps({'type': 'done', 'content': ''})}\n\n"


def get_dashboard_payload(user_id: str | None = None) -> dict[str, Any]:
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

    uid = {"user_id": user_id}

    pattern_rows = _conn.query("SELECT name, category, occurrences FROM pattern WHERE user_id = $user_id ORDER BY occurrences DESC", uid)
    if not pattern_rows or isinstance(pattern_rows, str):
        pattern_rows = []

    ifs_rows = _conn.query("SELECT name, role, description, occurrences FROM ifs_part WHERE user_id = $user_id ORDER BY occurrences DESC", uid)
    ifs_rows = [] if (not ifs_rows or isinstance(ifs_rows, str)) else ifs_rows

    schema_rows = _conn.query("SELECT name, domain, coping_style, description, occurrences FROM schema_pattern WHERE user_id = $user_id ORDER BY occurrences DESC", uid)
    schema_rows = [] if (not schema_rows or isinstance(schema_rows, str)) else schema_rows

    emotion_rows = _conn.query("SELECT name, valence, intensity FROM emotion WHERE user_id = $user_id ORDER BY intensity DESC", uid)
    emotion_rows = [] if (not emotion_rows or isinstance(emotion_rows, str)) else emotion_rows

    people_rows = _conn.query("SELECT name, relationship, description, occurrences FROM person WHERE user_id = $user_id ORDER BY occurrences DESC", uid)
    people_rows = [] if (not people_rows or isinstance(people_rows, str)) else people_rows

    body_rows = _conn.query("SELECT name, location, occurrences FROM body_signal WHERE user_id = $user_id ORDER BY occurrences DESC", uid)
    body_rows = [] if (not body_rows or isinstance(body_rows, str)) else body_rows

    co_occurrences = _conn.query("SELECT in.name AS pattern_a, out.name AS pattern_b, count AS times FROM co_occurs_with WHERE in.user_id = $user_id ORDER BY times DESC LIMIT 10", uid)
    if co_occurrences is None or isinstance(co_occurrences, str):
        co_occurrences = []

    reflections_total = _conn.query("SELECT count() AS total FROM reflection WHERE user_id = $user_id GROUP ALL", uid)
    total_reflections = reflections_total[0]["total"] if reflections_total and not isinstance(reflections_total, str) else 0

    themes_rows = _conn.query("SELECT name FROM theme WHERE user_id = $user_id", uid) or []
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


def get_people_overview_payload(user_id: str | None = None) -> dict[str, Any]:
    _init()
    from .agent import _conn

    if _conn is None:
        return {
            "people": [],
            "relationship_mix": [],
            "top_trigger_patterns": [],
            "summary": {
                "total_people": 0,
                "total_mentions": 0,
                "unique_relationships": 0,
                "top_person": None,
                "top_person_mentions": 0,
                "top_relationship": None,
                "key_action": "Add a few reflections first so relationship insights can be generated.",
            },
        }

    uid = {"user_id": user_id}

    people_rows = _conn.query(
        "SELECT id, name, relationship, description, occurrences, first_seen, last_seen FROM person WHERE user_id = $user_id ORDER BY occurrences DESC",
        uid,
    )
    if not people_rows or isinstance(people_rows, str):
        people_rows = []

    relationship_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"people_count": 0, "mentions": 0})
    trigger_pattern_counts: dict[str, dict[str, Any]] = {}
    people_payload: list[dict[str, Any]] = []
    total_mentions = 0

    for row in people_rows:
        if not isinstance(row, dict):
            continue

        person_id = row.get("id")
        person_name = str(row.get("name") or "").strip()
        if not person_name:
            continue
        relationship = str(row.get("relationship") or "other").strip().lower() or "other"
        description = str(row.get("description") or "").strip()
        occurrences = int(row.get("occurrences") or 0)
        first_seen = row.get("first_seen")
        last_seen = row.get("last_seen")

        relationship_counts[relationship]["people_count"] += 1
        relationship_counts[relationship]["mentions"] += occurrences
        total_mentions += occurrences

        trigger_rows = []
        if person_id:
            trigger_rows = _conn.query(
                "SELECT out.name AS name, out.category AS category FROM triggers_pattern WHERE in = $person_id",
                {"person_id": person_id},
            )
            if not trigger_rows or isinstance(trigger_rows, str):
                trigger_rows = []

        trigger_map: dict[str, dict[str, Any]] = {}
        for trigger in trigger_rows:
            if not isinstance(trigger, dict):
                continue
            trigger_name = str(trigger.get("name") or "").strip()
            if not trigger_name:
                continue
            trigger_category = str(trigger.get("category") or "unknown").strip().lower() or "unknown"
            trigger_key = trigger_name.lower()

            if trigger_key not in trigger_map:
                trigger_map[trigger_key] = {"name": trigger_name, "category": trigger_category, "links": 0}
            trigger_map[trigger_key]["links"] += 1

            if trigger_key not in trigger_pattern_counts:
                trigger_pattern_counts[trigger_key] = {"name": trigger_name, "category": trigger_category, "links": 0}
            trigger_pattern_counts[trigger_key]["links"] += 1

        triggered_patterns = sorted(trigger_map.values(), key=lambda item: (-item["links"], item["name"].lower()))

        people_payload.append(
            {
                "id": str(person_id) if person_id is not None else person_name.lower().replace(" ", "-"),
                "name": person_name,
                "relationship": relationship,
                "description": description,
                "occurrences": occurrences,
                "first_seen": first_seen,
                "last_seen": last_seen,
                "triggered_patterns": triggered_patterns,
            }
        )

    people_payload.sort(key=lambda item: (-item["occurrences"], item["name"].lower()))
    relationship_mix = sorted(
        (
            {"relationship": rel, "people_count": counts["people_count"], "mentions": counts["mentions"]}
            for rel, counts in relationship_counts.items()
        ),
        key=lambda item: (-item["mentions"], item["relationship"]),
    )
    top_trigger_patterns = sorted(
        trigger_pattern_counts.values(),
        key=lambda item: (-item["links"], item["name"].lower()),
    )[:12]

    top_person = people_payload[0] if people_payload else None
    top_relationship = relationship_mix[0]["relationship"] if relationship_mix else None

    if top_person and top_person["triggered_patterns"]:
        dominant_pattern = top_person["triggered_patterns"][0]["name"]
        key_action = (
            f"Run one small boundary experiment with {top_person['name']} this week, "
            f"then journal whether '{dominant_pattern}' felt weaker or stronger."
        )
    elif top_person:
        key_action = (
            f"Track your next interaction with {top_person['name']} and note the first emotion and body signal that appears."
        )
    else:
        key_action = "Add reflections that mention people so relationship actions can be surfaced."

    return {
        "people": people_payload,
        "relationship_mix": relationship_mix,
        "top_trigger_patterns": top_trigger_patterns,
        "summary": {
            "total_people": len(people_payload),
            "total_mentions": total_mentions,
            "unique_relationships": len(relationship_mix),
            "top_person": top_person["name"] if top_person else None,
            "top_person_mentions": top_person["occurrences"] if top_person else 0,
            "top_relationship": top_relationship,
            "key_action": key_action,
        },
    }


def get_reflections(user_id: str | None = None) -> list[dict[str, Any]]:
    _init()
    from .agent import _conn

    if _conn is None:
        return []

    rows = _conn.query(
        "SELECT id, text, daily_prompt, source, created_at FROM reflection WHERE user_id = $user_id ORDER BY created_at DESC",
        {"user_id": user_id},
    )
    if not rows or isinstance(rows, str):
        return []

    parsed: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        parsed.append(
            {
                "id": str(row.get("id", "")),
                "text": row.get("text", ""),
                "daily_prompt": row.get("daily_prompt"),
                "source": _normalize_reflection_source(row.get("source")),
                "created_at": row.get("created_at"),
            }
        )
    return parsed


def daily_prompt() -> str:
    return get_daily_prompt()
