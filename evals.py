"""Synapse Pipeline Evals — run with: uv run python evals.py"""

import json
import time
from langsmith import traceable, Client
from reflect.agent import build_reflection_graph, _init
from reflect.db import get_connection
from reflect.chat_agent import build_chat_agent
from langchain_core.messages import HumanMessage


client = Client()

# ═══════════════════════════════════════════════════
# EVAL 1: Extraction Quality
# ═══════════════════════════════════════════════════

EXTRACTION_CASES = [
    {
        "name": "abandonment_with_people",
        "text": "My friend Jake cancelled dinner again. I immediately thought he doesn't care about me. My chest got tight and I felt like crying. It reminds me of when my mum used to forget to pick me up from school.",
        "expect_patterns": ["fear of abandonment", "jumping to conclusions"],
        "expect_people": ["Jake", "mum"],
        "expect_emotions_valence": ["negative"],
        "expect_body_signals": True,
        "expect_ifs_or_schema": True,
    },
    {
        "name": "perfectionism_no_people",
        "text": "Spent all evening rewriting a two-paragraph email. I kept thinking every word had to be perfect or people would think I'm incompetent. I'm exhausted.",
        "expect_patterns": ["perfectionism"],
        "expect_people": [],
        "expect_emotions_valence": ["negative"],
        "expect_body_signals": False,
        "expect_ifs_or_schema": True,
    },
    {
        "name": "positive_progress",
        "text": "I actually said no to my boss today when she asked me to take on extra work. My heart was racing but I did it. She said that's fine. I feel proud of myself.",
        "expect_patterns": [],  # could detect people-pleasing progress or boundary-setting
        "expect_people": ["boss"],
        "expect_emotions_valence": ["positive"],
        "expect_body_signals": True,  # heart racing
        "expect_ifs_or_schema": False,
    },
]


@traceable(run_type="chain", name="eval_extraction")
def eval_extraction():
    """Test extraction quality on known reflections."""
    graph = build_reflection_graph()
    results = []

    for case in EXTRACTION_CASES:
        print(f"\n--- Extraction: {case['name']} ---")
        config = {"configurable": {"thread_id": f"eval-extract-{case['name']}"}}

        start = time.time()
        result = graph.invoke(
            {"reflection_text": case["text"], "daily_prompt": None, "messages": []},
            config=config,
        )
        elapsed = time.time() - start

        extracted = result.get("extracted", {})
        patterns = [p["name"].lower() for p in extracted.get("patterns", [])]
        people = [p["name"].lower() for p in extracted.get("people", [])]
        emotions = extracted.get("emotions", [])
        ifs_parts = extracted.get("ifs_parts", [])
        schemas = extracted.get("schemas", [])
        body_signals = extracted.get("body_signals", [])

        checks = {}

        # Check expected patterns found (fuzzy — check if expected term is substring of any detected pattern)
        if case["expect_patterns"]:
            for exp in case["expect_patterns"]:
                found = any(exp.lower() in p for p in patterns)
                checks[f"pattern_{exp}"] = "PASS" if found else "FAIL"
                if not found:
                    print(f"  MISS: expected pattern '{exp}', got {patterns}")

        # Check people detected
        if case["expect_people"]:
            for exp in case["expect_people"]:
                found = any(exp.lower() in p for p in people)
                checks[f"person_{exp}"] = "PASS" if found else "FAIL"
                if not found:
                    print(f"  MISS: expected person '{exp}', got {people}")

        # Check emotion valence
        if case["expect_emotions_valence"]:
            valences = [e.get("valence", "") for e in emotions]
            for exp_val in case["expect_emotions_valence"]:
                found = exp_val in valences
                checks[f"emotion_{exp_val}"] = "PASS" if found else "FAIL"

        # Check body signals presence
        if case["expect_body_signals"]:
            checks["body_signals"] = "PASS" if body_signals else "FAIL"

        # Check IFS/schema presence
        if case["expect_ifs_or_schema"]:
            has_depth = bool(ifs_parts or schemas)
            checks["ifs_or_schema"] = "PASS" if has_depth else "FAIL"

        passed = sum(1 for v in checks.values() if v == "PASS")
        total = len(checks)
        score = passed / total if total > 0 else 1.0

        print(f"  Patterns: {patterns}")
        print(f"  People: {people}")
        print(f"  IFS parts: {[p['name'] for p in ifs_parts]}")
        print(f"  Schemas: {[s['name'] for s in schemas]}")
        print(f"  Body signals: {[b['name'] for b in body_signals]}")
        print(f"  Time: {elapsed:.1f}s")
        print(f"  Score: {passed}/{total} ({score:.0%})")
        print(f"  Checks: {checks}")

        results.append({
            "case": case["name"],
            "score": score,
            "checks": checks,
            "elapsed": elapsed,
            "extracted": extracted,
        })

    return results


# ═══════════════════════════════════════════════════
# EVAL 2: Graph Integrity
# ═══════════════════════════════════════════════════

@traceable(run_type="chain", name="eval_graph_integrity")
def eval_graph_integrity():
    """Check graph is well-formed — no orphans, duplicates, or broken edges."""
    conn = get_connection()
    checks = {}

    # 1. No orphaned reflections (every reflection should have at least one edge)
    orphans = conn.query(
        """SELECT id, text FROM reflection
           WHERE array::len(->reveals) = 0
           AND array::len(->expresses) = 0
           AND array::len(->about) = 0"""
    )
    orphan_count = len(orphans) if orphans and not isinstance(orphans, str) else 0
    checks["no_orphaned_reflections"] = "PASS" if orphan_count == 0 else f"FAIL ({orphan_count} orphans)"
    print(f"Orphaned reflections: {orphan_count}")

    # 2. All patterns have occurrences > 0
    zero_occ = conn.query("SELECT name FROM pattern WHERE occurrences <= 0")
    zero_count = len(zero_occ) if zero_occ and not isinstance(zero_occ, str) else 0
    checks["pattern_occurrences_valid"] = "PASS" if zero_count == 0 else f"FAIL ({zero_count})"
    print(f"Patterns with zero occurrences: {zero_count}")

    # 3. Check for near-duplicate patterns (case-insensitive)
    all_patterns = conn.query("SELECT name FROM pattern")
    if all_patterns and not isinstance(all_patterns, str):
        names = [p["name"].lower().strip() for p in all_patterns]
        dupes = set()
        for i, n1 in enumerate(names):
            for n2 in names[i+1:]:
                if n1 == n2:
                    dupes.add(n1)
        checks["no_exact_duplicates"] = "PASS" if not dupes else f"FAIL: {dupes}"
        print(f"Exact duplicate patterns: {dupes or 'none'}")

    # 4. Check for near-duplicate people (mum vs Mum)
    all_people = conn.query("SELECT name FROM person")
    if all_people and not isinstance(all_people, str):
        names = [p["name"] for p in all_people]
        lower_names = [n.lower().strip() for n in names]
        people_dupes = {}
        for i, n1 in enumerate(lower_names):
            for j, n2 in enumerate(lower_names[i+1:], i+1):
                if n1 == n2 and names[i] != names[j]:
                    people_dupes[n1] = (names[i], names[j])
        checks["no_people_duplicates"] = "PASS" if not people_dupes else f"FAIL: {people_dupes}"
        print(f"Duplicate people (case diff): {people_dupes or 'none'}")

    # 5. Co-occurrence edges are symmetric and valid
    co_edges = conn.query("SELECT in.name AS a, out.name AS b, count FROM co_occurs_with")
    if co_edges and not isinstance(co_edges, str):
        invalid = [e for e in co_edges if e.get("count", 0) <= 0]
        checks["co_occurrence_valid"] = "PASS" if not invalid else f"FAIL ({len(invalid)} invalid)"
        print(f"Co-occurrence edges: {len(co_edges)} total, {len(invalid)} invalid")

    # 6. All IFS parts have valid roles
    ifs_parts = conn.query("SELECT name, role FROM ifs_part")
    if ifs_parts and not isinstance(ifs_parts, str):
        valid_roles = {"exile", "manager", "firefighter"}
        bad_roles = [p for p in ifs_parts if p.get("role", "").lower() not in valid_roles]
        checks["ifs_roles_valid"] = "PASS" if not bad_roles else f"FAIL: {bad_roles}"
        print(f"IFS parts with invalid roles: {len(bad_roles)}")

    # 7. Embeddings present on nodes
    for table in ["pattern", "ifs_part", "schema_pattern", "person"]:
        result = conn.query(f"SELECT count() AS c FROM {table} WHERE embedding != NONE GROUP ALL")
        with_emb = result[0]["c"] if result and not isinstance(result, str) else 0
        total = conn.query(f"SELECT count() AS c FROM {table} GROUP ALL")
        total_count = total[0]["c"] if total and not isinstance(total, str) else 0
        pct = (with_emb / total_count * 100) if total_count > 0 else 0
        checks[f"{table}_embeddings"] = "PASS" if pct >= 80 else f"FAIL ({with_emb}/{total_count})"
        print(f"{table} embeddings: {with_emb}/{total_count} ({pct:.0f}%)")

    # Summary
    passed = sum(1 for v in checks.values() if v == "PASS")
    total = len(checks)
    print(f"\nGraph integrity: {passed}/{total} checks passed")
    print(json.dumps(checks, indent=2))

    return checks


# ═══════════════════════════════════════════════════
# EVAL 3: Chat Agent Grounding
# ═══════════════════════════════════════════════════

CHAT_CASES = [
    {
        "name": "top_pattern",
        "question": "What is my most common pattern?",
        "must_mention": ["emotional dysregulation"],  # highest occurrence from seed data
        "must_not_mention": [],
    },
    {
        "name": "dad_relationship",
        "question": "How does my relationship with my dad affect me?",
        "must_mention": ["dad"],
        "must_not_mention": [],
    },
    {
        "name": "no_hallucination",
        "question": "Do I have any patterns related to gambling?",
        "must_mention": [],
        "must_not_mention": ["gambling addiction", "you gamble frequently"],
    },
]


@traceable(run_type="chain", name="eval_chat_grounding")
def eval_chat_grounding():
    """Test chat agent uses real graph data and doesn't hallucinate."""
    agent = build_chat_agent()
    results = []

    for case in CHAT_CASES:
        print(f"\n--- Chat: {case['name']} ---")
        print(f"  Q: {case['question']}")

        config = {"configurable": {"thread_id": f"eval-chat-{case['name']}"}}

        start = time.time()
        result = agent.invoke(
            {"messages": [HumanMessage(content=case["question"])]},
            config=config,
        )
        elapsed = time.time() - start

        answer = result["messages"][-1].content.lower()
        print(f"  A: {answer[:200]}...")

        checks = {}

        # Check must-mention terms
        for term in case["must_mention"]:
            found = term.lower() in answer
            checks[f"mentions_{term}"] = "PASS" if found else "FAIL"
            if not found:
                print(f"  MISS: expected mention of '{term}'")

        # Check must-not-mention terms (hallucination check)
        for term in case["must_not_mention"]:
            found = term.lower() in answer
            checks[f"no_hallucinate_{term}"] = "PASS" if not found else "FAIL"
            if found:
                print(f"  HALLUCINATION: mentioned '{term}' but shouldn't have")

        passed = sum(1 for v in checks.values() if v == "PASS")
        total = len(checks)
        score = passed / total if total > 0 else 1.0

        print(f"  Time: {elapsed:.1f}s")
        print(f"  Score: {passed}/{total} ({score:.0%})")

        results.append({
            "case": case["name"],
            "score": score,
            "checks": checks,
            "elapsed": elapsed,
        })

    return results


# ═══════════════════════════════════════════════════
# EVAL 4: Pipeline Performance
# ═══════════════════════════════════════════════════

@traceable(run_type="chain", name="eval_performance")
def eval_performance():
    """Measure pipeline latency — find bottlenecks."""
    graph = build_reflection_graph()

    test_text = "Had a fight with my partner today and I shut down completely. I went quiet and she got frustrated. I know I do this because of how my parents used to argue. My chest felt tight and I couldn't breathe properly."

    config = {"configurable": {"thread_id": "eval-perf"}}

    start = time.time()
    result = graph.invoke(
        {"reflection_text": test_text, "daily_prompt": None, "messages": []},
        config=config,
    )
    total = time.time() - start

    extracted = result.get("extracted", {})
    print(f"Total pipeline time: {total:.1f}s")
    print(f"Patterns extracted: {len(extracted.get('patterns', []))}")
    print(f"People found: {len(extracted.get('people', []))}")
    print(f"IFS parts: {len(extracted.get('ifs_parts', []))}")
    print(f"Schemas: {len(extracted.get('schemas', []))}")
    print(f"Body signals: {len(extracted.get('body_signals', []))}")
    print(f"\n(Check LangSmith for per-node timing breakdown)")

    return {"total_seconds": total, "extracted_counts": {
        "patterns": len(extracted.get("patterns", [])),
        "people": len(extracted.get("people", [])),
        "ifs_parts": len(extracted.get("ifs_parts", [])),
        "schemas": len(extracted.get("schemas", [])),
        "body_signals": len(extracted.get("body_signals", [])),
    }}


# ═══════════════════════════════════════════════════
# Run all evals
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("EVAL 1: Extraction Quality")
    print("=" * 60)
    extraction_results = eval_extraction()

    print("\n" + "=" * 60)
    print("EVAL 2: Graph Integrity")
    print("=" * 60)
    integrity_results = eval_graph_integrity()

    print("\n" + "=" * 60)
    print("EVAL 3: Chat Agent Grounding")
    print("=" * 60)
    chat_results = eval_chat_grounding()

    print("\n" + "=" * 60)
    print("EVAL 4: Pipeline Performance")
    print("=" * 60)
    perf_results = eval_performance()

    # ── Summary ──
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    ext_avg = sum(r["score"] for r in extraction_results) / len(extraction_results)
    print(f"Extraction quality: {ext_avg:.0%}")

    integrity_passed = sum(1 for v in integrity_results.values() if v == "PASS")
    integrity_total = len(integrity_results)
    print(f"Graph integrity: {integrity_passed}/{integrity_total}")

    chat_avg = sum(r["score"] for r in chat_results) / len(chat_results)
    print(f"Chat grounding: {chat_avg:.0%}")

    print(f"Pipeline latency: {perf_results['total_seconds']:.1f}s")
    print(f"\nAll traces visible in LangSmith under eval_* runs.")
