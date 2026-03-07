import json
from typing import Annotated, TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.documents import Document
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langsmith import traceable

from .db import get_connection, get_embeddings, get_vector_store, init_schema
from .graph_store import (
    make_graph_tools,
    store_reflection_record,
    upsert_pattern,
    upsert_theme,
    upsert_emotion,
    upsert_ifs_part,
    upsert_schema,
    upsert_person,
    upsert_body_signal,
    create_edges,
    query_co_occurrences,
    query_negative_emotion_triggers,
    query_central_patterns,
)
from .extraction import extract_with_agent
from .prompts import INSIGHT_PROMPT, FOLLOWUP_PROMPT


class ReflectionState(TypedDict):
    reflection_text: str
    daily_prompt: str | None
    reflection_id: str
    extracted: dict
    graph_connections: list
    insights: str
    follow_up_questions: list[str]
    messages: Annotated[list, add_messages]


# ── Shared resources (initialized once) ──
_conn = None
_vector_store = None
_extraction_tools = None
_chat_tools = None


def _init():
    global _conn, _vector_store, _extraction_tools, _chat_tools
    if _conn is None:
        _conn = get_connection()
        init_schema(_conn)
        embeddings = get_embeddings()
        _vector_store = get_vector_store(_conn, embeddings)
        _extraction_tools, _chat_tools = make_graph_tools(_conn, _vector_store)


def get_chat_tools():
    _init()
    return _chat_tools


# ── Node functions ──

@traceable(run_type="chain", name="store_reflection")
def store_reflection(state: ReflectionState) -> dict:
    _init()
    text = state["reflection_text"]
    prompt = state.get("daily_prompt")

    # Store as graph record
    rid = store_reflection_record(_conn, text, prompt)

    # Also add to vector store for semantic search
    doc = Document(page_content=text, metadata={"id": rid, "daily_prompt": prompt or ""})
    _vector_store.add_documents(documents=[doc], ids=[rid.replace(":", "_")])

    return {"reflection_id": rid}


@traceable(run_type="chain", name="extract_patterns")
def extract_patterns(state: ReflectionState) -> dict:
    _init()
    extracted = extract_with_agent(state["reflection_text"], _extraction_tools)
    return {"extracted": extracted}


@traceable(run_type="chain", name="update_graph")
def update_graph(state: ReflectionState) -> dict:
    _init()
    extracted = state["extracted"]
    rid = state["reflection_id"]

    pattern_ids = []
    for p in extracted.get("patterns", []):
        pid = upsert_pattern(_conn, p["name"], p["category"], p["description"])
        pattern_ids.append(pid)

    theme_ids = []
    for t in extracted.get("themes", []):
        tid = upsert_theme(_conn, t["name"], t["description"])
        theme_ids.append(tid)

    emotion_ids = []
    for e in extracted.get("emotions", []):
        eid = upsert_emotion(_conn, e["name"], e["valence"], e["intensity"])
        emotion_ids.append(eid)

    ifs_part_ids = []
    for part in extracted.get("ifs_parts", []):
        pid = upsert_ifs_part(_conn, part["name"], part["role"], part["description"])
        ifs_part_ids.append(pid)

    schema_ids = []
    for s in extracted.get("schemas", []):
        sid = upsert_schema(_conn, s["name"], s["domain"], s.get("coping_style", "none"), s["description"])
        schema_ids.append(sid)

    person_ids = []
    for p in extracted.get("people", []):
        pid = upsert_person(_conn, p["name"], p["relationship"], p.get("description", ""))
        person_ids.append(pid)

    body_signal_ids = []
    for b in extracted.get("body_signals", []):
        bid = upsert_body_signal(_conn, b["name"], b.get("location", "other"))
        body_signal_ids.append(bid)

    create_edges(_conn, rid, pattern_ids, emotion_ids, theme_ids, extracted, ifs_part_ids, schema_ids, person_ids, body_signal_ids)
    return {}


@traceable(run_type="chain", name="query_graph")
def query_graph(state: ReflectionState) -> dict:
    _init()
    connections = []

    co = query_co_occurrences(_conn)
    if co:
        connections.append({"type": "co_occurrences", "data": co})

    neg = query_negative_emotion_triggers(_conn)
    if neg:
        connections.append({"type": "negative_triggers", "data": neg})

    central = query_central_patterns(_conn)
    if central:
        connections.append({"type": "central_patterns", "data": central})

    return {"graph_connections": connections}


@traceable(run_type="chain", name="generate_insights")
def generate_insights(state: ReflectionState) -> dict:
    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
    prompt_text = INSIGHT_PROMPT.format(
        reflection_text=state["reflection_text"],
        extracted=json.dumps(state["extracted"], default=str),
        graph_connections=json.dumps(state["graph_connections"], default=str),
    )
    response = llm.invoke(prompt_text)
    return {"insights": response.content}


@traceable(run_type="chain", name="generate_followups")
def generate_followups(state: ReflectionState) -> dict:
    llm = ChatOpenAI(model="gpt-4o", temperature=0.8)
    extracted = state["extracted"]
    patterns_str = json.dumps([p["name"] for p in extracted.get("patterns", [])], default=str)
    people_str = json.dumps([p["name"] for p in extracted.get("people", [])], default=str)
    body_str = json.dumps([b["name"] for b in extracted.get("body_signals", [])], default=str)
    prompt_text = FOLLOWUP_PROMPT.format(
        patterns=patterns_str,
        people=people_str,
        body_signals=body_str,
        insights=state["insights"],
    )
    response = llm.invoke(prompt_text)
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        questions = json.loads(content.strip())
    except (json.JSONDecodeError, IndexError):
        questions = ["What do you notice about this pattern?", "How does this make you feel?", "What would you like to change?"]
    return {"follow_up_questions": questions}


# ── Build the graph ──

def build_reflection_graph():
    builder = StateGraph(ReflectionState)

    builder.add_node("store_reflection", store_reflection)
    builder.add_node("extract_patterns", extract_patterns)
    builder.add_node("update_graph", update_graph)
    builder.add_node("query_graph", query_graph)
    builder.add_node("generate_insights", generate_insights)
    builder.add_node("generate_followups", generate_followups)

    builder.add_edge(START, "store_reflection")
    builder.add_edge("store_reflection", "extract_patterns")
    builder.add_edge("extract_patterns", "update_graph")
    builder.add_edge("update_graph", "query_graph")
    builder.add_edge("query_graph", "generate_insights")
    builder.add_edge("generate_insights", "generate_followups")
    builder.add_edge("generate_followups", END)

    return builder.compile(checkpointer=MemorySaver())
