import json
import re
from langchain_core.tools import tool
from langsmith import traceable
from surrealdb import Surreal


def _slug(name: str) -> str:
    """Convert a name to a safe SurrealDB record ID slug."""
    return re.sub(r"[^a-z0-9_]", "_", name.lower().strip())


# ──────────────────────────────────────────────
# Graph CRUD operations
# ──────────────────────────────────────────────

@traceable(run_type="tool", name="store_reflection_record")
def store_reflection_record(conn: Surreal, text: str, daily_prompt: str | None = None) -> str:
    """Store a reflection as a record and return its ID."""
    result = conn.query(
        "CREATE reflection SET text = $text, daily_prompt = $prompt",
        {"text": text, "prompt": daily_prompt},
    )
    record_id = result[0]["id"]
    return str(record_id)


@traceable(run_type="tool", name="upsert_pattern")
def upsert_pattern(conn: Surreal, name: str, category: str, description: str) -> str:
    result = conn.query(
        """UPDATE pattern SET
            name = $name,
            category = $category,
            description = $description,
            occurrences += 1,
            last_seen = time::now()
        WHERE name = $name""",
        {"name": name, "category": category, "description": description},
    )
    if not result:
        result = conn.query(
            "CREATE pattern SET name = $name, category = $category, description = $description",
            {"name": name, "category": category, "description": description},
        )
    return str(result[0]["id"])


@traceable(run_type="tool", name="upsert_theme")
def upsert_theme(conn: Surreal, name: str, description: str) -> str:
    result = conn.query(
        "UPDATE theme SET name = $name, description = $description WHERE name = $name",
        {"name": name, "description": description},
    )
    if not result:
        result = conn.query(
            "CREATE theme SET name = $name, description = $description",
            {"name": name, "description": description},
        )
    return str(result[0]["id"])


@traceable(run_type="tool", name="upsert_ifs_part")
def upsert_ifs_part(conn: Surreal, name: str, role: str, description: str) -> str:
    result = conn.query(
        """UPDATE ifs_part SET
            name = $name,
            role = $role,
            description = $description,
            occurrences += 1,
            last_seen = time::now()
        WHERE name = $name""",
        {"name": name, "role": role, "description": description},
    )
    if not result or isinstance(result, str):
        result = conn.query(
            "CREATE ifs_part SET name = $name, role = $role, description = $description, occurrences = 1",
            {"name": name, "role": role, "description": description},
        )
    return str(result[0]["id"])


@traceable(run_type="tool", name="upsert_schema")
def upsert_schema(conn: Surreal, name: str, domain: str, coping_style: str, description: str) -> str:
    result = conn.query(
        """UPDATE schema_pattern SET
            name = $name,
            domain = $domain,
            coping_style = $coping_style,
            description = $description,
            occurrences += 1,
            last_seen = time::now()
        WHERE name = $name""",
        {"name": name, "domain": domain, "coping_style": coping_style, "description": description},
    )
    if not result or isinstance(result, str):
        result = conn.query(
            "CREATE schema_pattern SET name = $name, domain = $domain, coping_style = $coping_style, description = $description, occurrences = 1",
            {"name": name, "domain": domain, "coping_style": coping_style, "description": description},
        )
    return str(result[0]["id"])


@traceable(run_type="tool", name="upsert_emotion")
def upsert_emotion(conn: Surreal, name: str, valence: str, intensity: float) -> str:
    result = conn.query(
        "UPDATE emotion SET name = $name, valence = $valence, intensity = $intensity WHERE name = $name",
        {"name": name, "valence": valence, "intensity": intensity},
    )
    if not result:
        result = conn.query(
            "CREATE emotion SET name = $name, valence = $valence, intensity = $intensity",
            {"name": name, "valence": valence, "intensity": intensity},
        )
    return str(result[0]["id"])


@traceable(run_type="tool", name="create_edges")
def create_edges(
    conn: Surreal,
    reflection_id: str,
    pattern_ids: list[str],
    emotion_ids: list[str],
    theme_ids: list[str],
    extracted: dict,
    ifs_part_ids: list[str] | None = None,
    schema_ids: list[str] | None = None,
):
    """Create all graph edges for a reflection."""
    # reflection -> reveals -> pattern
    for i, pid in enumerate(pattern_ids):
        strength = extracted["patterns"][i].get("strength", 1.0) if i < len(extracted["patterns"]) else 1.0
        conn.query(
            f"RELATE {reflection_id}->reveals->{pid} SET strength = $strength",
            {"strength": strength},
        )

    # reflection -> expresses -> emotion
    for i, eid in enumerate(emotion_ids):
        intensity = extracted["emotions"][i].get("intensity", 0.5) if i < len(extracted["emotions"]) else 0.5
        conn.query(
            f"RELATE {reflection_id}->expresses->{eid} SET intensity = $intensity",
            {"intensity": intensity},
        )

    # reflection -> about -> theme
    for tid in theme_ids:
        conn.query(f"RELATE {reflection_id}->about->{tid}")

    # pattern co-occurrence edges
    for i, p1 in enumerate(pattern_ids):
        for p2 in pattern_ids[i + 1:]:
            existing = conn.query(
                f"SELECT * FROM co_occurs_with WHERE in = {p1} AND out = {p2}"
            )
            if existing:
                conn.query(
                    f"UPDATE co_occurs_with SET count += 1 WHERE in = {p1} AND out = {p2}"
                )
            else:
                conn.query(
                    f"RELATE {p1}->co_occurs_with->{p2} SET count = 1"
                )

    # emotion -> triggered_by -> theme
    for eid in emotion_ids:
        for tid in theme_ids:
            conn.query(f"RELATE {eid}->triggered_by->{tid}")

    # reflection -> activates -> ifs_part
    for part_id in (ifs_part_ids or []):
        conn.query(f"RELATE {reflection_id}->activates->{part_id}")

    # reflection -> triggers_schema -> schema_pattern
    for sid in (schema_ids or []):
        conn.query(f"RELATE {reflection_id}->triggers_schema->{sid}")

    # ifs_part -> protects_against -> schema_pattern (parts often protect against schema pain)
    for part_id in (ifs_part_ids or []):
        for sid in (schema_ids or []):
            conn.query(f"RELATE {part_id}->protects_against->{sid}")


# ──────────────────────────────────────────────
# SurrealQL Graph Traversal Queries
# ──────────────────────────────────────────────

@traceable(run_type="tool", name="query_patterns_by_theme")
def query_patterns_by_theme(conn: Surreal, theme_name: str) -> list[dict]:
    """Multi-hop: What patterns emerge from a given theme?"""
    return conn.query(
        """SELECT name, category FROM pattern
           WHERE <-reveals<-reflection->about->theme.name CONTAINS $theme""",
        {"theme": theme_name},
    )


@traceable(run_type="tool", name="query_co_occurrences")
def query_co_occurrences(conn: Surreal) -> list[dict]:
    """Pattern co-occurrence: what shows up together?"""
    return conn.query(
        """SELECT in.name AS pattern_a, out.name AS pattern_b, count AS times
           FROM co_occurs_with ORDER BY times DESC LIMIT 10"""
    )


@traceable(run_type="tool", name="query_pattern_evolution")
def query_pattern_evolution(conn: Surreal, category: str = "cognitive") -> list[dict]:
    """Temporal: pattern evolution over time."""
    return conn.query(
        """SELECT created_at, ->reveals->pattern[WHERE category = $cat].name AS patterns
           FROM reflection ORDER BY created_at""",
        {"cat": category},
    )


@traceable(run_type="tool", name="query_negative_emotion_triggers")
def query_negative_emotion_triggers(conn: Surreal) -> list[dict]:
    """2-hop: What themes trigger negative emotions?"""
    return conn.query(
        """SELECT in.name AS emotion, out.name AS theme
           FROM triggered_by WHERE in.valence = 'negative'"""
    )


@traceable(run_type="tool", name="query_central_patterns")
def query_central_patterns(conn: Surreal) -> list[dict]:
    """Graph connectivity: most connected patterns."""
    return conn.query(
        """SELECT name, category,
                  array::len(->co_occurs_with) + array::len(<-co_occurs_with) AS connections
           FROM pattern ORDER BY connections DESC LIMIT 5"""
    )


@traceable(run_type="tool", name="query_all_patterns")
def query_all_patterns(conn: Surreal) -> list[dict]:
    """Get all existing pattern nodes."""
    return conn.query("SELECT name, category, occurrences FROM pattern ORDER BY occurrences DESC")


# ──────────────────────────────────────────────
# LangGraph Agent Tools (need conn injected)
# ──────────────────────────────────────────────

def make_graph_tools(conn: Surreal, vector_store):
    """Create @tool-decorated functions with conn/vector_store baked in."""

    @tool
    def retrieve_similar_reflections(query: str) -> str:
        """Search past reflections by semantic similarity. Use this to find context before extracting patterns."""
        results = vector_store.similarity_search_with_score(query=query, k=5)
        if not results:
            return "No past reflections found."
        lines = []
        for doc, score in results:
            lines.append(f"[dist={score:.3f}] {doc.page_content}")
        return "\n".join(lines)

    @tool
    def get_existing_patterns() -> str:
        """Get all existing pattern nodes from the graph. Use this before extraction to reuse existing pattern names."""
        patterns = query_all_patterns(conn)
        if not patterns:
            return "No patterns exist yet."
        return json.dumps(patterns, default=str)

    @tool
    def get_emotion_triggers(emotion_name: str) -> str:
        """Find what themes trigger a specific emotion via graph traversal."""
        data = conn.query(
            """SELECT out.name AS theme FROM triggered_by WHERE in.name = $emotion""",
            {"emotion": emotion_name},
        )
        return json.dumps(data, default=str) if data else f"No triggers found for {emotion_name}"

    @tool
    def get_pattern_connections(pattern_name: str) -> str:
        """Find patterns that co-occur with the given pattern, plus linked reflections."""
        co = conn.query(
            """SELECT out.name AS co_pattern, count AS times
               FROM co_occurs_with WHERE in.name = $name
               ORDER BY times DESC LIMIT 5""",
            {"name": pattern_name},
        )
        refs = conn.query(
            """SELECT <-reveals<-reflection.text AS reflections
               FROM pattern WHERE name = $name""",
            {"name": pattern_name},
        )
        return json.dumps({
            "co_occurring": co,
            "reflections": refs,
        }, default=str)

    @tool
    def get_temporal_evolution(pattern_name: str) -> str:
        """Show how a pattern appears over time across reflections."""
        data = conn.query(
            """SELECT created_at, text FROM reflection
               WHERE ->reveals->pattern.name CONTAINS $name
               ORDER BY created_at""",
            {"name": pattern_name},
        )
        return json.dumps(data, default=str) if data else f"No timeline data for {pattern_name}"

    @tool
    def semantic_search_reflections(query: str) -> str:
        """Search reflections by meaning, then show their graph connections (patterns + themes)."""
        results = vector_store.similarity_search_with_score(query=query, k=3)
        if not results:
            return "No matching reflections found."
        output = []
        for doc, score in results:
            output.append(f"[dist={score:.3f}] {doc.page_content}")
        return "\n---\n".join(output)

    @tool
    def get_all_patterns_overview() -> str:
        """Get an overview of ALL patterns in the user's graph, ranked by how often they appear. Use this for broad questions like 'what patterns do I repeat?' or 'what are my most common patterns?'"""
        patterns = query_all_patterns(conn)
        if not patterns:
            return "No patterns found yet."
        co = query_co_occurrences(conn)
        central = query_central_patterns(conn)
        return json.dumps({
            "patterns_by_frequency": patterns,
            "top_co_occurrences": co,
            "most_connected_patterns": central,
        }, default=str)

    @tool
    def get_all_emotions_overview() -> str:
        """Get an overview of ALL emotions in the user's graph with their triggers. Use this for broad questions like 'when do I get most emotional?' or 'what emotions come up most?'"""
        emotions = conn.query(
            "SELECT name, valence, intensity FROM emotion ORDER BY intensity DESC"
        )
        triggers = query_negative_emotion_triggers(conn)
        return json.dumps({
            "all_emotions": emotions,
            "negative_emotion_triggers": triggers,
        }, default=str)

    @tool
    def get_graph_summary() -> str:
        """Get a high-level summary of the entire reflection graph — counts of patterns, emotions, themes, reflections, and key connections. Use this when the user asks general questions about their data."""
        patterns = query_all_patterns(conn)
        emotions = conn.query("SELECT name, valence FROM emotion")
        themes = conn.query("SELECT name FROM theme")
        reflections = conn.query("SELECT count() AS total FROM reflection GROUP ALL")
        co = query_co_occurrences(conn)
        return json.dumps({
            "total_reflections": reflections[0]["total"] if reflections else 0,
            "total_patterns": len(patterns),
            "total_emotions": len(emotions),
            "total_themes": len(themes),
            "top_patterns": patterns[:5],
            "emotions": emotions,
            "top_co_occurrences": co[:5],
        }, default=str)

    @tool
    def get_ifs_parts_overview() -> str:
        """Get all IFS inner parts (exiles, managers, firefighters) found across reflections. Use this for questions about inner parts, protective patterns, childhood wounds, or why the user behaves in certain ways."""
        parts = conn.query(
            "SELECT name, role, description, occurrences FROM ifs_part ORDER BY occurrences DESC"
        )
        if not parts or isinstance(parts, str):
            return "No IFS parts identified yet."
        # Get which reflections activated each part
        for part in parts:
            refs = conn.query(
                """SELECT <-activates<-reflection.text AS reflections
                   FROM ifs_part WHERE name = $name""",
                {"name": part["name"]},
            )
            part["source_reflections"] = refs[0].get("reflections", []) if refs and not isinstance(refs, str) else []
        return json.dumps(parts, default=str)

    @tool
    def get_schemas_overview() -> str:
        """Get all early maladaptive schemas (Schema Therapy) found across reflections. Use this for questions about deep life patterns, childhood origins, family dynamics, why patterns keep repeating, or what drives certain behaviors."""
        schemas = conn.query(
            "SELECT name, domain, coping_style, description, occurrences FROM schema_pattern ORDER BY occurrences DESC"
        )
        if not schemas or isinstance(schemas, str):
            return "No schema patterns identified yet."
        for s in schemas:
            refs = conn.query(
                """SELECT <-triggers_schema<-reflection.text AS reflections
                   FROM schema_pattern WHERE name = $name""",
                {"name": s["name"]},
            )
            s["source_reflections"] = refs[0].get("reflections", []) if refs and not isinstance(refs, str) else []
        return json.dumps(schemas, default=str)

    @tool
    def get_deep_pattern_analysis(pattern_name: str) -> str:
        """Get a deep analysis of a specific pattern — its co-occurring patterns, linked IFS parts, activated schemas, and the actual reflection text where it appeared. Use this when the user asks WHY a pattern exists or wants to understand its roots."""
        # Get the pattern's reflections
        refs = conn.query(
            """SELECT <-reveals<-reflection.text AS reflections
               FROM pattern WHERE name = $name""",
            {"name": pattern_name},
        )
        # Get co-occurring patterns
        co = conn.query(
            """SELECT out.name AS co_pattern, count AS times
               FROM co_occurs_with WHERE in.name = $name
               ORDER BY times DESC LIMIT 5""",
            {"name": pattern_name},
        )
        # Get IFS parts that appear in the same reflections
        ifs_parts = conn.query(
            """SELECT name, role, description FROM ifs_part
               WHERE <-activates<-reflection->reveals->pattern.name CONTAINS $name""",
            {"name": pattern_name},
        )
        # Get schemas that appear in the same reflections
        schemas = conn.query(
            """SELECT name, domain, coping_style, description FROM schema_pattern
               WHERE <-triggers_schema<-reflection->reveals->pattern.name CONTAINS $name""",
            {"name": pattern_name},
        )
        return json.dumps({
            "pattern": pattern_name,
            "reflections": refs[0].get("reflections", []) if refs and not isinstance(refs, str) else [],
            "co_occurring_patterns": co if co and not isinstance(co, str) else [],
            "linked_ifs_parts": ifs_parts if ifs_parts and not isinstance(ifs_parts, str) else [],
            "linked_schemas": schemas if schemas and not isinstance(schemas, str) else [],
        }, default=str)

    extraction_tools = [retrieve_similar_reflections, get_existing_patterns]
    chat_tools = [
        get_all_patterns_overview,
        get_all_emotions_overview,
        get_ifs_parts_overview,
        get_schemas_overview,
        get_deep_pattern_analysis,
        get_graph_summary,
        get_emotion_triggers,
        get_pattern_connections,
        get_temporal_evolution,
        semantic_search_reflections,
    ]

    return extraction_tools, chat_tools
