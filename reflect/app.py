import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import plotly.graph_objects as go
from langchain_core.messages import HumanMessage

from reflect.agent import build_reflection_graph
from reflect.chat_agent import build_chat_agent
from reflect.prompts import get_daily_prompt

st.set_page_config(page_title="ReflectGraph", page_icon="*", layout="wide")
st.title("ReflectGraph")
st.caption("Self-reflection powered by knowledge graphs")

# ── Initialize session state ──
if "reflection_graph" not in st.session_state:
    with st.spinner("Connecting to SurrealDB and building agents..."):
        st.session_state.reflection_graph = build_reflection_graph()
        st.session_state.chat_agent = build_chat_agent()
        st.session_state.reflection_count = 0
        st.session_state.chat_messages = []

graph = st.session_state.reflection_graph
chat_agent = st.session_state.chat_agent

# ── Sidebar: Daily Prompt ──
with st.sidebar:
    st.header("Daily Prompt")
    if "daily_prompt" not in st.session_state:
        st.session_state.daily_prompt = get_daily_prompt()
    st.info(st.session_state.daily_prompt)
    if st.button("New Prompt"):
        st.session_state.daily_prompt = get_daily_prompt()
        st.rerun()
    if st.button("Use This Prompt"):
        st.session_state.use_prompt = True
        st.rerun()

# ── Tabs ──
tab1, tab2, tab3 = st.tabs(["Reflect", "My Patterns", "Ask"])

# ── Tab 1: Reflect ──
with tab1:
    default_text = st.session_state.daily_prompt if st.session_state.get("use_prompt") else ""
    if st.session_state.get("use_prompt"):
        st.session_state.use_prompt = False

    reflection_text = st.text_area(
        "What's on your mind?",
        value=default_text,
        height=200,
        placeholder="Write your reflection here...",
    )

    if st.button("Submit Reflection", type="primary", disabled=not reflection_text.strip()):
        st.session_state.reflection_count += 1
        config = {"configurable": {"thread_id": f"session-{st.session_state.reflection_count}"}}

        with st.spinner("Analyzing your reflection..."):
            result = graph.invoke(
                {
                    "reflection_text": reflection_text,
                    "daily_prompt": st.session_state.daily_prompt,
                    "messages": [],
                },
                config=config,
            )

        st.success("Reflection processed!")

        # Show extracted patterns
        col1, col2, col3 = st.columns(3)
        extracted = result.get("extracted", {})

        with col1:
            st.subheader("Patterns")
            for p in extracted.get("patterns", []):
                st.metric(p["name"], f"{p.get('strength', 0):.0%}", p["category"])

        with col2:
            st.subheader("Emotions")
            for e in extracted.get("emotions", []):
                emoji = {"positive": "+", "negative": "-", "neutral": "~"}.get(e["valence"], "")
                st.metric(e["name"], f"{e.get('intensity', 0):.0%}", emoji)

        with col3:
            st.subheader("Themes")
            for t in extracted.get("themes", []):
                st.write(f"**{t['name']}**: {t['description']}")

        # IFS Parts & Schemas
        ifs_parts = extracted.get("ifs_parts", [])
        schemas = extracted.get("schemas", [])
        if ifs_parts or schemas:
            st.divider()
            col_ifs, col_schema = st.columns(2)
            with col_ifs:
                st.subheader("Inner Parts (IFS)")
                for part in ifs_parts:
                    role_icon = {"exile": "inner child", "manager": "protector", "firefighter": "reactor"}.get(part["role"], part["role"])
                    st.write(f"**{part['name']}** ({role_icon}): {part['description']}")
            with col_schema:
                st.subheader("Schema Patterns")
                for s in schemas:
                    coping = f" | coping: {s['coping_style']}" if s.get("coping_style", "none") != "none" else ""
                    st.write(f"**{s['name']}** ({s['domain']}{coping}): {s['description']}")

        # People & Body Signals
        people = extracted.get("people", [])
        body_signals = extracted.get("body_signals", [])
        if people or body_signals:
            st.divider()
            col_people, col_body = st.columns(2)
            with col_people:
                st.subheader("People")
                for p in people:
                    st.write(f"**{p['name']}** ({p['relationship']}): {p.get('description', '')}")
            with col_body:
                st.subheader("Body Signals")
                for b in body_signals:
                    st.write(f"**{b['name']}** ({b.get('location', '')})")

        # Insights
        st.divider()
        st.subheader("Insights")
        st.write(result.get("insights", ""))

        # Follow-up questions
        st.subheader("Follow-up Questions")
        for q in result.get("follow_up_questions", []):
            st.write(f"- {q}")

# ── Tab 2: My Patterns ──
with tab2:
    from reflect.agent import _conn, _init

    _init()
    if _conn:
        try:
            pattern_data = _conn.query("SELECT name, category, occurrences FROM pattern ORDER BY occurrences DESC")

            if pattern_data and not isinstance(pattern_data, str):

                COLORS = {
                    "cognitive": "#FF6B6B",
                    "emotional": "#4ECDC4",
                    "relational": "#45B7D1",
                    "behavioral": "#96CEB4",
                }

                # ── Helper: horizontal bar for a list of patterns ──
                def _pattern_bar(patterns, color, height=200):
                    if not patterns:
                        st.caption("None detected yet")
                        return
                    names = [p["name"] for p in patterns]
                    counts = [p.get("occurrences", 1) for p in patterns]
                    fig = go.Figure(go.Bar(
                        x=counts, y=names, orientation="h",
                        marker_color=color,
                        text=counts, textposition="outside",
                    ))
                    fig.update_layout(
                        height=height,
                        margin=dict(l=0, r=30, t=5, b=5),
                        xaxis=dict(visible=False),
                        yaxis=dict(autorange="reversed", tickfont=dict(size=13)),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="white"),
                        bargap=0.35,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # ── Top 5 per category ──
                categories = [
                    ("Cognitive Patterns", "cognitive"),
                    ("Emotional Patterns", "emotional"),
                    ("Relational Patterns", "relational"),
                    ("Behavioral Patterns", "behavioral"),
                ]

                col1, col2 = st.columns(2)
                for i, (label, cat) in enumerate(categories):
                    with col1 if i % 2 == 0 else col2:
                        st.subheader(label)
                        cat_patterns = [p for p in pattern_data if p.get("category") == cat][:5]
                        _pattern_bar(cat_patterns, COLORS[cat])

                st.divider()

                # ── IFS Parts + Schemas side by side ──
                col_ifs, col_schema = st.columns(2)

                ifs_parts = _conn.query("SELECT name, role, description, occurrences FROM ifs_part ORDER BY occurrences DESC")
                schema_data = _conn.query("SELECT name, domain, coping_style, description, occurrences FROM schema_pattern ORDER BY occurrences DESC")

                with col_ifs:
                    st.subheader("Inner Parts (IFS)")
                    if ifs_parts and not isinstance(ifs_parts, str):
                        ROLE_COLORS = {"exile": "#FF6B6B", "manager": "#4ECDC4", "firefighter": "#FFD93D"}
                        ROLE_ICONS = {"exile": "inner child", "manager": "protector", "firefighter": "reactor"}
                        for part in ifs_parts[:8]:
                            role = part.get("role", "")
                            color = ROLE_COLORS.get(role, "#ccc")
                            icon = ROLE_ICONS.get(role, role)
                            occ = part.get("occurrences", 1)
                            bar_width = min(occ * 12, 100)
                            st.markdown(
                                f'<div style="margin-bottom:10px;">'
                                f'<span style="color:{color};font-weight:bold;">{part["name"]}</span> '
                                f'<span style="color:#888;font-size:0.85em;">({icon})</span><br/>'
                                f'<div style="background:{color}33;border-radius:4px;height:8px;width:100%;margin-top:3px;">'
                                f'<div style="background:{color};border-radius:4px;height:8px;width:{bar_width}%;"></div>'
                                f'</div>'
                                f'<span style="color:#aaa;font-size:0.8em;">{part.get("description", "")}</span>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                    else:
                        st.caption("No IFS parts detected yet.")

                with col_schema:
                    st.subheader("Schema Patterns")
                    if schema_data and not isinstance(schema_data, str):
                        DOMAIN_COLORS = {
                            "disconnection": "#FF6B6B", "impaired_autonomy": "#4ECDC4",
                            "impaired_limits": "#45B7D1", "other_directedness": "#96CEB4",
                            "overvigilance": "#FFD93D",
                        }
                        COPING_LABELS = {"surrender": "gives in", "avoidance": "avoids", "overcompensation": "fights back"}
                        for s in schema_data[:8]:
                            domain = s.get("domain", "")
                            color = DOMAIN_COLORS.get(domain, "#ccc")
                            occ = s.get("occurrences", 1)
                            bar_width = min(occ * 12, 100)
                            coping = s.get("coping_style", "none")
                            coping_text = f" — {COPING_LABELS.get(coping, '')}" if coping != "none" else ""
                            st.markdown(
                                f'<div style="margin-bottom:10px;">'
                                f'<span style="color:{color};font-weight:bold;">{s["name"]}</span> '
                                f'<span style="color:#888;font-size:0.85em;">({domain.replace("_", " ")}{coping_text})</span><br/>'
                                f'<div style="background:{color}33;border-radius:4px;height:8px;width:100%;margin-top:3px;">'
                                f'<div style="background:{color};border-radius:4px;height:8px;width:{bar_width}%;"></div>'
                                f'</div>'
                                f'<span style="color:#aaa;font-size:0.8em;">{s.get("description", "")}</span>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                    else:
                        st.caption("No schema patterns detected yet.")

                st.divider()

                # ── Emotion Map ──
                st.subheader("Emotions")
                emotions = _conn.query("SELECT name, valence, intensity FROM emotion ORDER BY intensity DESC")
                if emotions and not isinstance(emotions, str):
                    pos = [e for e in emotions if e.get("valence") == "positive"]
                    neg = [e for e in emotions if e.get("valence") == "negative"]
                    neu = [e for e in emotions if e.get("valence") == "neutral"]

                    col_neg, col_neu, col_pos = st.columns(3)
                    with col_neg:
                        st.markdown("**Negative**")
                        for e in neg[:6]:
                            pct = int(e.get("intensity", 0.5) * 100)
                            st.markdown(
                                f'{e["name"]} '
                                f'<span style="color:#FF6B6B;">{"█" * (pct // 10)}{"░" * (10 - pct // 10)}</span> '
                                f'<span style="color:#888;">{pct}%</span>',
                                unsafe_allow_html=True,
                            )
                    with col_neu:
                        st.markdown("**Neutral**")
                        for e in neu[:6]:
                            pct = int(e.get("intensity", 0.5) * 100)
                            st.markdown(
                                f'{e["name"]} '
                                f'<span style="color:#888;">{"█" * (pct // 10)}{"░" * (10 - pct // 10)}</span> '
                                f'<span style="color:#888;">{pct}%</span>',
                                unsafe_allow_html=True,
                            )
                    with col_pos:
                        st.markdown("**Positive**")
                        for e in pos[:6]:
                            pct = int(e.get("intensity", 0.5) * 100)
                            st.markdown(
                                f'{e["name"]} '
                                f'<span style="color:#4ECDC4;">{"█" * (pct // 10)}{"░" * (10 - pct // 10)}</span> '
                                f'<span style="color:#888;">{pct}%</span>',
                                unsafe_allow_html=True,
                            )

                st.divider()

                # ── People & Body Signals ──
                col_people, col_body = st.columns(2)

                people_data = _conn.query("SELECT name, relationship, description, occurrences FROM person ORDER BY occurrences DESC")
                body_data = _conn.query("SELECT name, location, occurrences FROM body_signal ORDER BY occurrences DESC")

                with col_people:
                    st.subheader("People in Your Reflections")
                    if people_data and not isinstance(people_data, str):
                        REL_COLORS = {
                            "parent": "#FF6B6B", "sibling": "#FFD93D", "partner": "#DDA0DD",
                            "friend": "#4ECDC4", "colleague": "#45B7D1", "authority": "#96CEB4",
                            "therapist": "#A8D8EA", "other": "#ccc",
                        }
                        for p in people_data[:8]:
                            rel = p.get("relationship", "other")
                            color = REL_COLORS.get(rel, "#ccc")
                            occ = p.get("occurrences", 1)
                            bar_width = min(occ * 15, 100)
                            st.markdown(
                                f'<div style="margin-bottom:10px;">'
                                f'<span style="color:{color};font-weight:bold;">{p["name"]}</span> '
                                f'<span style="color:#888;font-size:0.85em;">({rel})</span><br/>'
                                f'<div style="background:{color}33;border-radius:4px;height:8px;width:100%;margin-top:3px;">'
                                f'<div style="background:{color};border-radius:4px;height:8px;width:{bar_width}%;"></div>'
                                f'</div>'
                                f'<span style="color:#aaa;font-size:0.8em;">{p.get("description", "")}</span>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                    else:
                        st.caption("No people detected yet.")

                with col_body:
                    st.subheader("Body Signals")
                    if body_data and not isinstance(body_data, str):
                        BODY_COLOR = "#E8A87C"
                        for b in body_data[:8]:
                            occ = b.get("occurrences", 1)
                            bar_width = min(occ * 15, 100)
                            st.markdown(
                                f'<div style="margin-bottom:10px;">'
                                f'<span style="color:{BODY_COLOR};font-weight:bold;">{b["name"]}</span> '
                                f'<span style="color:#888;font-size:0.85em;">({b.get("location", "")})</span><br/>'
                                f'<div style="background:{BODY_COLOR}33;border-radius:4px;height:8px;width:100%;margin-top:3px;">'
                                f'<div style="background:{BODY_COLOR};border-radius:4px;height:8px;width:{bar_width}%;"></div>'
                                f'</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )
                    else:
                        st.caption("No body signals detected yet.")

            else:
                st.info("No patterns yet. Submit a reflection to get started!")
        except Exception as e:
            st.error(f"Could not load patterns: {e}")
    else:
        st.info("Connecting...")

# ── Tab 3: Ask Your Graph ──
with tab3:
    st.subheader("Ask about your patterns")
    st.caption("Ask questions like: 'Why do I always feel anxious?' or 'What patterns do I repeat?'")

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if user_input := st.chat_input("Ask about your patterns..."):
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        config = {"configurable": {"thread_id": "chat-session"}}

        with st.chat_message("assistant"):
            with st.spinner("Searching your graph..."):
                result = chat_agent.invoke(
                    {"messages": [HumanMessage(content=user_input)]},
                    config=config,
                )
                answer = result["messages"][-1].content
                st.write(answer)

        st.session_state.chat_messages.append({"role": "assistant", "content": answer})
