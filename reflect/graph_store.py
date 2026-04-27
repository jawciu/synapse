import json
import re
from langchain_core.tools import tool
from langsmith import traceable
from surrealdb import Surreal

_embeddings_model = None


def set_embeddings_model(model):
    global _embeddings_model
    _embeddings_model = model


def _embed(text: str) -> list[float] | None:
    """Embed text using the shared embeddings model. Returns None if not available."""
    if _embeddings_model is None:
        return None
    return _embeddings_model.embed_query(text)


def _embed_batch(texts: list[str]) -> list[list[float] | None]:
    """Embed multiple texts in a single API call. Returns [None, ...] if model unavailable."""
    if _embeddings_model is None:
        return [None] * len(texts)
    return _embeddings_model.embed_documents(texts)


def _slug(name: str) -> str:
    """Convert a name to a safe SurrealDB record ID slug."""
    return re.sub(r"[^a-z0-9_]", "_", name.lower().strip())


# ──────────────────────────────────────────────
# Graph CRUD operations
# ──────────────────────────────────────────────

@traceable(run_type="tool", name="store_reflection_record")
def store_reflection_record(conn: Surreal, text: str, daily_prompt: str | None = None, source: str | None = None, user_id: str | None = None) -> str:
    """Store a reflection as a record and return its ID."""
    result = conn.query(
        "CREATE reflection SET text = $text, daily_prompt = $prompt, source = $source, user_id = $user_id",
        {"text": text, "prompt": daily_prompt, "source": source, "user_id": user_id},
    )
    record_id = result[0]["id"]
    return str(record_id)


@traceable(run_type="tool", name="upsert_pattern")
def upsert_pattern(conn: Surreal, name: str, category: str, description: str, user_id: str | None = None, embedding: list[float] | None = None) -> str:
    name = name.strip().lower()
    category = category.strip().lower()
    if embedding is None:
        embedding = _embed(f"{name}: {description}")
    result = conn.query(
        """UPDATE pattern SET
            name = $name,
            category = $category,
            description = $description,
            embedding = $embedding,
            occurrences += 1,
            last_seen = time::now()
        WHERE name = $name AND user_id = $user_id""",
        {"name": name, "category": category, "description": description, "embedding": embedding, "user_id": user_id},
    )
    if not result:
        result = conn.query(
            "CREATE pattern SET name = $name, category = $category, description = $description, embedding = $embedding, user_id = $user_id",
            {"name": name, "category": category, "description": description, "embedding": embedding, "user_id": user_id},
        )
    return str(result[0]["id"])


THEME_DEDUP_DISTANCE = 0.42  # cosine distance; ≤ this collapses to existing theme. Tuned empirically against real data — embeddings include description so literal-concept matches sit ~0.38, while related-but-distinct concepts (e.g. "fear of failure" vs "achievement-driven anxiety") sit ~0.46+.


@traceable(run_type="tool", name="upsert_theme")
def upsert_theme(conn: Surreal, name: str, description: str, user_id: str | None = None, embedding: list[float] | None = None) -> str:
    name = name.strip().lower()
    if embedding is None:
        embedding = _embed(f"{name}: {description}")

    # Exact-name match first — cheapest path.
    result = conn.query(
        "UPDATE theme SET name = $name, description = $description, embedding = $embedding WHERE name = $name AND user_id = $user_id",
        {"name": name, "description": description, "embedding": embedding, "user_id": user_id},
    )
    if result:
        return str(result[0]["id"])

    # Semantic-near match — alias to existing theme if cosine distance ≤ threshold.
    near = conn.query(
        """SELECT name, vector::distance::knn() AS dist FROM theme
           WHERE embedding <|1,COSINE|> $embedding AND user_id = $user_id
           ORDER BY dist LIMIT 1""",
        {"embedding": embedding, "user_id": user_id},
    )
    if near and not isinstance(near, str) and near[0].get("dist") is not None and near[0]["dist"] <= THEME_DEDUP_DISTANCE:
        canonical = near[0]["name"]
        aliased = conn.query(
            "SELECT id FROM theme WHERE name = $name AND user_id = $user_id",
            {"name": canonical, "user_id": user_id},
        )
        if aliased and not isinstance(aliased, str):
            return str(aliased[0]["id"])

    # No match — create new theme.
    result = conn.query(
        "CREATE theme SET name = $name, description = $description, embedding = $embedding, user_id = $user_id",
        {"name": name, "description": description, "embedding": embedding, "user_id": user_id},
    )
    return str(result[0]["id"])


@traceable(run_type="tool", name="upsert_ifs_part")
def upsert_ifs_part(conn: Surreal, name: str, role: str, description: str, user_id: str | None = None, embedding: list[float] | None = None) -> str:
    name = name.strip().lower()
    role = role.strip().lower()
    if embedding is None:
        embedding = _embed(f"IFS {role}: {name} — {description}")
    result = conn.query(
        """UPDATE ifs_part SET
            name = $name,
            role = $role,
            description = $description,
            embedding = $embedding,
            occurrences += 1,
            last_seen = time::now()
        WHERE name = $name AND user_id = $user_id""",
        {"name": name, "role": role, "description": description, "embedding": embedding, "user_id": user_id},
    )
    if not result or isinstance(result, str):
        result = conn.query(
            "CREATE ifs_part SET name = $name, role = $role, description = $description, embedding = $embedding, occurrences = 1, user_id = $user_id",
            {"name": name, "role": role, "description": description, "embedding": embedding, "user_id": user_id},
        )
    return str(result[0]["id"])


@traceable(run_type="tool", name="upsert_schema")
def upsert_schema(conn: Surreal, name: str, domain: str, coping_style: str, description: str, user_id: str | None = None, embedding: list[float] | None = None) -> str:
    name = name.strip().lower()
    domain = domain.strip().lower()
    coping_style = coping_style.strip().lower()
    if embedding is None:
        embedding = _embed(f"Schema {name} ({domain}): {description}")
    result = conn.query(
        """UPDATE schema_pattern SET
            name = $name,
            domain = $domain,
            coping_style = $coping_style,
            description = $description,
            embedding = $embedding,
            occurrences += 1,
            last_seen = time::now()
        WHERE name = $name AND user_id = $user_id""",
        {"name": name, "domain": domain, "coping_style": coping_style, "description": description, "embedding": embedding, "user_id": user_id},
    )
    if not result or isinstance(result, str):
        result = conn.query(
            "CREATE schema_pattern SET name = $name, domain = $domain, coping_style = $coping_style, description = $description, embedding = $embedding, occurrences = 1, user_id = $user_id",
            {"name": name, "domain": domain, "coping_style": coping_style, "description": description, "embedding": embedding, "user_id": user_id},
        )
    return str(result[0]["id"])


@traceable(run_type="tool", name="upsert_emotion")
def upsert_emotion(conn: Surreal, name: str, valence: str, intensity: float, user_id: str | None = None) -> str:
    name = name.strip().lower()
    valence = valence.strip().lower()
    result = conn.query(
        "UPDATE emotion SET name = $name, valence = $valence, intensity = $intensity WHERE name = $name AND user_id = $user_id",
        {"name": name, "valence": valence, "intensity": intensity, "user_id": user_id},
    )
    if not result:
        result = conn.query(
            "CREATE emotion SET name = $name, valence = $valence, intensity = $intensity, user_id = $user_id",
            {"name": name, "valence": valence, "intensity": intensity, "user_id": user_id},
        )
    return str(result[0]["id"])


@traceable(run_type="tool", name="upsert_person")
def upsert_person(conn: Surreal, name: str, relationship: str, description: str, user_id: str | None = None, embedding: list[float] | None = None) -> str:
    name = name.strip().title()  # "mum" and "Mum" -> "Mum"
    if embedding is None:
        embedding = _embed(f"{name} ({relationship}): {description}")
    result = conn.query(
        """UPDATE person SET
            name = $name,
            relationship = $relationship,
            description = $description,
            embedding = $embedding,
            occurrences += 1,
            last_seen = time::now()
        WHERE name = $name AND user_id = $user_id""",
        {"name": name, "relationship": relationship, "description": description, "embedding": embedding, "user_id": user_id},
    )
    if not result or isinstance(result, str):
        result = conn.query(
            "CREATE person SET name = $name, relationship = $relationship, description = $description, embedding = $embedding, occurrences = 1, user_id = $user_id",
            {"name": name, "relationship": relationship, "description": description, "embedding": embedding, "user_id": user_id},
        )
    return str(result[0]["id"])


@traceable(run_type="tool", name="upsert_body_signal")
def upsert_body_signal(conn: Surreal, name: str, location: str, user_id: str | None = None) -> str:
    name = name.strip().lower()
    location = location.strip().lower()
    result = conn.query(
        "UPDATE body_signal SET name = $name, location = $location, occurrences += 1 WHERE name = $name AND user_id = $user_id",
        {"name": name, "location": location, "user_id": user_id},
    )
    if not result or isinstance(result, str):
        result = conn.query(
            "CREATE body_signal SET name = $name, location = $location, occurrences = 1, user_id = $user_id",
            {"name": name, "location": location, "user_id": user_id},
        )
    return str(result[0]["id"])


@traceable(run_type="tool", name="batch_upsert_entities")
def batch_upsert_entities(conn: Surreal, extracted: dict, user_id: str | None = None) -> dict:
    """Upsert all extracted entities with a single batched embedding call.

    Collects embedding texts from all embeddable entity types, calls
    _embed_batch() once, then distributes the pre-computed embeddings
    to individual upsert functions. Emotions and body signals (which
    have no embeddings) are upserted directly.

    Returns a dict of ID lists keyed by entity type.
    """
    # -- 1. Collect texts that need embeddings --------------------------------
    embed_texts: list[str] = []
    # Track (entity_type, index_in_extracted_list) for each text so we can
    # distribute embeddings back after the batch call.
    embed_map: list[tuple[str, int]] = []

    for i, p in enumerate(extracted.get("patterns", [])):
        name = p["name"].strip().lower()
        embed_texts.append(f"{name}: {p['description']}")
        embed_map.append(("pattern", i))

    for i, t in enumerate(extracted.get("themes", [])):
        name = t["name"].strip().lower()
        embed_texts.append(f"{name}: {t['description']}")
        embed_map.append(("theme", i))

    for i, part in enumerate(extracted.get("ifs_parts", [])):
        name = part["name"].strip().lower()
        role = part["role"].strip().lower()
        embed_texts.append(f"IFS {role}: {name} — {part['description']}")
        embed_map.append(("ifs_part", i))

    for i, s in enumerate(extracted.get("schemas", [])):
        name = s["name"].strip().lower()
        domain = s["domain"].strip().lower()
        embed_texts.append(f"Schema {name} ({domain}): {s['description']}")
        embed_map.append(("schema", i))

    for i, p in enumerate(extracted.get("people", [])):
        name = p["name"].strip().title()
        embed_texts.append(f"{name} ({p['relationship']}): {p.get('description', '')}")
        embed_map.append(("person", i))

    # -- 2. Single batched embedding call -------------------------------------
    all_embeddings = _embed_batch(embed_texts) if embed_texts else []

    # Build lookup: (entity_type, index) -> embedding vector
    embedding_lookup: dict[tuple[str, int], list[float] | None] = {}
    for idx, (etype, eidx) in enumerate(embed_map):
        embedding_lookup[(etype, eidx)] = all_embeddings[idx]

    # -- 3. Upsert each entity type with pre-computed embeddings --------------
    pattern_ids = []
    for i, p in enumerate(extracted.get("patterns", [])):
        pid = upsert_pattern(
            conn, p["name"], p["category"], p["description"],
            user_id=user_id,
            embedding=embedding_lookup.get(("pattern", i)),
        )
        pattern_ids.append(pid)

    theme_ids = []
    for i, t in enumerate(extracted.get("themes", [])):
        tid = upsert_theme(
            conn, t["name"], t["description"],
            user_id=user_id,
            embedding=embedding_lookup.get(("theme", i)),
        )
        theme_ids.append(tid)

    emotion_ids = []
    for e in extracted.get("emotions", []):
        eid = upsert_emotion(
            conn, e["name"], e["valence"], e["intensity"],
            user_id=user_id,
        )
        emotion_ids.append(eid)

    ifs_part_ids = []
    for i, part in enumerate(extracted.get("ifs_parts", [])):
        partid = upsert_ifs_part(
            conn, part["name"], part["role"], part["description"],
            user_id=user_id,
            embedding=embedding_lookup.get(("ifs_part", i)),
        )
        ifs_part_ids.append(partid)

    schema_ids = []
    for i, s in enumerate(extracted.get("schemas", [])):
        sid = upsert_schema(
            conn, s["name"], s["domain"], s.get("coping_style", "none"), s["description"],
            user_id=user_id,
            embedding=embedding_lookup.get(("schema", i)),
        )
        schema_ids.append(sid)

    person_ids = []
    for i, p in enumerate(extracted.get("people", [])):
        pid = upsert_person(
            conn, p["name"], p["relationship"], p.get("description", ""),
            user_id=user_id,
            embedding=embedding_lookup.get(("person", i)),
        )
        person_ids.append(pid)

    body_signal_ids = []
    for b in extracted.get("body_signals", []):
        bid = upsert_body_signal(
            conn, b["name"], b.get("location", "other"),
            user_id=user_id,
        )
        body_signal_ids.append(bid)

    return {
        "pattern_ids": pattern_ids,
        "theme_ids": theme_ids,
        "emotion_ids": emotion_ids,
        "ifs_part_ids": ifs_part_ids,
        "schema_ids": schema_ids,
        "person_ids": person_ids,
        "body_signal_ids": body_signal_ids,
    }


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
    person_ids: list[str] | None = None,
    body_signal_ids: list[str] | None = None,
):
    """Create all graph edges for a reflection."""
    BATCH_SIZE = 50
    statements: list[str] = []

    # reflection -> reveals -> pattern (with strength metadata)
    for i, pid in enumerate(pattern_ids):
        strength = extracted["patterns"][i].get("strength", 1.0) if i < len(extracted["patterns"]) else 1.0
        statements.append(
            f"RELATE {reflection_id}->reveals->{pid} SET strength = {strength}"
        )

    # reflection -> expresses -> emotion (with intensity metadata)
    for i, eid in enumerate(emotion_ids):
        intensity = extracted["emotions"][i].get("intensity", 0.5) if i < len(extracted["emotions"]) else 0.5
        statements.append(
            f"RELATE {reflection_id}->expresses->{eid} SET intensity = {intensity}"
        )

    # reflection -> about -> theme
    for tid in theme_ids:
        statements.append(f"RELATE {reflection_id}->about->{tid}")

    # emotion -> triggered_by -> theme
    for eid in emotion_ids:
        for tid in theme_ids:
            statements.append(f"RELATE {eid}->triggered_by->{tid}")

    # reflection -> activates -> ifs_part
    for part_id in (ifs_part_ids or []):
        statements.append(f"RELATE {reflection_id}->activates->{part_id}")

    # reflection -> triggers_schema -> schema_pattern
    for sid in (schema_ids or []):
        statements.append(f"RELATE {reflection_id}->triggers_schema->{sid}")

    # ifs_part -> protects_against -> schema_pattern
    for part_id in (ifs_part_ids or []):
        for sid in (schema_ids or []):
            statements.append(f"RELATE {part_id}->protects_against->{sid}")

    # reflection -> mentions -> person
    for pid in (person_ids or []):
        statements.append(f"RELATE {reflection_id}->mentions->{pid}")

    # person -> triggers_pattern -> pattern
    for pid in (person_ids or []):
        for pat_id in pattern_ids:
            statements.append(f"RELATE {pid}->triggers_pattern->{pat_id}")

    # reflection -> feels_in_body -> body_signal
    for bid in (body_signal_ids or []):
        statements.append(f"RELATE {reflection_id}->feels_in_body->{bid}")

    # Execute simple RELATE statements in batches
    for i in range(0, len(statements), BATCH_SIZE):
        batch = statements[i : i + BATCH_SIZE]
        conn.query("; ".join(batch))

    # Pattern co-occurrence edges (need conditional logic, kept as individual queries)
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


# ──────────────────────────────────────────────
# SurrealQL Graph Traversal Queries
# ──────────────────────────────────────────────

@traceable(run_type="tool", name="query_patterns_by_theme")
def query_patterns_by_theme(conn: Surreal, theme_name: str, user_id: str | None = None) -> list[dict]:
    """Multi-hop: What patterns emerge from a given theme?"""
    return conn.query(
        """SELECT name, category FROM pattern
           WHERE <-reveals<-reflection->about->theme.name CONTAINS $theme AND user_id = $user_id""",
        {"theme": theme_name, "user_id": user_id},
    )


@traceable(run_type="tool", name="query_co_occurrences")
def query_co_occurrences(conn: Surreal, user_id: str | None = None) -> list[dict]:
    """Pattern co-occurrence: what shows up together?"""
    return conn.query(
        """SELECT in.name AS pattern_a, out.name AS pattern_b, count AS times
           FROM co_occurs_with WHERE in.user_id = $user_id ORDER BY times DESC LIMIT 10""",
        {"user_id": user_id},
    )


@traceable(run_type="tool", name="query_pattern_evolution")
def query_pattern_evolution(conn: Surreal, category: str = "cognitive", user_id: str | None = None) -> list[dict]:
    """Temporal: pattern evolution over time."""
    return conn.query(
        """SELECT created_at, ->reveals->pattern[WHERE category = $cat].name AS patterns
           FROM reflection WHERE user_id = $user_id ORDER BY created_at""",
        {"cat": category, "user_id": user_id},
    )


@traceable(run_type="tool", name="query_negative_emotion_triggers")
def query_negative_emotion_triggers(conn: Surreal, user_id: str | None = None) -> list[dict]:
    """2-hop: What themes trigger negative emotions?"""
    return conn.query(
        """SELECT in.name AS emotion, out.name AS theme
           FROM triggered_by WHERE in.valence = 'negative' AND in.user_id = $user_id""",
        {"user_id": user_id},
    )


@traceable(run_type="tool", name="query_central_patterns")
def query_central_patterns(conn: Surreal, user_id: str | None = None) -> list[dict]:
    """Graph connectivity: most connected patterns."""
    return conn.query(
        """SELECT name, category,
                  array::len(->co_occurs_with) + array::len(<-co_occurs_with) AS connections
           FROM pattern WHERE user_id = $user_id ORDER BY connections DESC LIMIT 5""",
        {"user_id": user_id},
    )


@traceable(run_type="tool", name="query_all_patterns")
def query_all_patterns(conn: Surreal, user_id: str | None = None) -> list[dict]:
    """Get all existing pattern nodes."""
    return conn.query(
        "SELECT name, category, occurrences FROM pattern WHERE user_id = $user_id ORDER BY occurrences DESC",
        {"user_id": user_id},
    )


# ──────────────────────────────────────────────
# LangGraph Agent Tools (need conn injected)
# ──────────────────────────────────────────────

def make_graph_tools(conn: Surreal, vector_store, user_id: str | None = None):
    """Create @tool-decorated functions with conn/vector_store/user_id baked in."""

    def _vs_search(query: str, k: int = 5):
        """Similarity search filtered to the current user."""
        try:
            return vector_store.similarity_search_with_score(
                query=query, k=k, filter={"user_id": user_id}
            )
        except TypeError:
            return vector_store.similarity_search_with_score(query=query, k=k)

    @tool
    def retrieve_similar_reflections(query: str) -> str:
        """Search past reflections by semantic similarity. Use this to find context before extracting patterns."""
        results = _vs_search(query, k=5)
        if not results:
            return "No past reflections found."
        lines = []
        for doc, score in results:
            lines.append(f"[dist={score:.3f}] {doc.page_content}")
        return "\n".join(lines)

    @tool
    def get_existing_patterns() -> str:
        """Get all existing pattern nodes from the graph. Use this before extraction to reuse existing pattern names."""
        patterns = query_all_patterns(conn, user_id=user_id)
        if not patterns:
            return "No patterns exist yet."
        return json.dumps(patterns, default=str)

    @tool
    def get_emotion_triggers(emotion_name: str) -> str:
        """Find what themes trigger a specific emotion via graph traversal."""
        data = conn.query(
            """SELECT out.name AS theme FROM triggered_by WHERE in.name = $emotion AND in.user_id = $user_id""",
            {"emotion": emotion_name, "user_id": user_id},
        )
        return json.dumps(data, default=str) if data else f"No triggers found for {emotion_name}"

    @tool
    def get_pattern_connections(pattern_name: str) -> str:
        """Find patterns that co-occur with the given pattern, plus linked reflections."""
        co = conn.query(
            """SELECT out.name AS co_pattern, count AS times
               FROM co_occurs_with WHERE in.name = $name AND in.user_id = $user_id
               ORDER BY times DESC LIMIT 5""",
            {"name": pattern_name, "user_id": user_id},
        )
        refs = conn.query(
            """SELECT <-reveals<-reflection.text AS reflections
               FROM pattern WHERE name = $name AND user_id = $user_id""",
            {"name": pattern_name, "user_id": user_id},
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
               WHERE ->reveals->pattern.name CONTAINS $name AND user_id = $user_id
               ORDER BY created_at""",
            {"name": pattern_name, "user_id": user_id},
        )
        return json.dumps(data, default=str) if data else f"No timeline data for {pattern_name}"

    @tool
    def semantic_search_reflections(query: str) -> str:
        """Search reflections by meaning, then show their graph connections (patterns + themes)."""
        results = _vs_search(query, k=3)
        if not results:
            return "No matching reflections found."
        output = []
        for doc, score in results:
            output.append(f"[dist={score:.3f}] {doc.page_content}")
        return "\n---\n".join(output)

    @tool
    def get_all_patterns_overview() -> str:
        """Get an overview of ALL patterns in the user's graph, ranked by how often they appear. Use this for broad questions like 'what patterns do I repeat?' or 'what are my most common patterns?'"""
        patterns = query_all_patterns(conn, user_id=user_id)
        if not patterns:
            return "No patterns found yet."
        co = query_co_occurrences(conn, user_id=user_id)
        central = query_central_patterns(conn, user_id=user_id)
        return json.dumps({
            "patterns_by_frequency": patterns,
            "top_co_occurrences": co,
            "most_connected_patterns": central,
        }, default=str)

    @tool
    def get_all_emotions_overview() -> str:
        """Get an overview of ALL emotions in the user's graph with their triggers. Use this for broad questions like 'when do I get most emotional?' or 'what emotions come up most?'"""
        emotions = conn.query(
            "SELECT name, valence, intensity FROM emotion WHERE user_id = $user_id ORDER BY intensity DESC",
            {"user_id": user_id},
        )
        triggers = query_negative_emotion_triggers(conn, user_id=user_id)
        return json.dumps({
            "all_emotions": emotions,
            "negative_emotion_triggers": triggers,
        }, default=str)

    @tool
    def get_graph_summary() -> str:
        """Get a high-level summary of the entire reflection graph — counts of patterns, emotions, themes, reflections, and key connections. Use this when the user asks general questions about their data."""
        patterns = query_all_patterns(conn, user_id=user_id)
        emotions = conn.query("SELECT name, valence FROM emotion WHERE user_id = $user_id", {"user_id": user_id})
        themes = conn.query("SELECT name FROM theme WHERE user_id = $user_id", {"user_id": user_id})
        reflections = conn.query(
            "SELECT count() AS total FROM reflection WHERE user_id = $user_id GROUP ALL",
            {"user_id": user_id},
        )
        co = query_co_occurrences(conn, user_id=user_id)
        return json.dumps({
            "total_reflections": reflections[0]["total"] if reflections else 0,
            "total_patterns": len(patterns),
            "total_emotions": len(emotions) if emotions else 0,
            "total_themes": len(themes) if themes else 0,
            "top_patterns": patterns[:5],
            "emotions": emotions,
            "top_co_occurrences": co[:5],
        }, default=str)

    @tool
    def get_ifs_parts_overview() -> str:
        """Get all IFS inner parts (exiles, managers, firefighters) found across reflections. Use this for questions about inner parts, protective patterns, childhood wounds, or why the user behaves in certain ways."""
        parts = conn.query(
            "SELECT name, role, description, occurrences FROM ifs_part WHERE user_id = $user_id ORDER BY occurrences DESC",
            {"user_id": user_id},
        )
        if not parts or isinstance(parts, str):
            return "No IFS parts identified yet."
        for part in parts:
            refs = conn.query(
                """SELECT <-activates<-reflection.text AS reflections
                   FROM ifs_part WHERE name = $name AND user_id = $user_id""",
                {"name": part["name"], "user_id": user_id},
            )
            part["source_reflections"] = refs[0].get("reflections", []) if refs and not isinstance(refs, str) else []
        return json.dumps(parts, default=str)

    @tool
    def get_schemas_overview() -> str:
        """Get all early maladaptive schemas (Schema Therapy) found across reflections. Use this for questions about deep life patterns, childhood origins, family dynamics, why patterns keep repeating, or what drives certain behaviors."""
        schemas = conn.query(
            "SELECT name, domain, coping_style, description, occurrences FROM schema_pattern WHERE user_id = $user_id ORDER BY occurrences DESC",
            {"user_id": user_id},
        )
        if not schemas or isinstance(schemas, str):
            return "No schema patterns identified yet."
        for s in schemas:
            refs = conn.query(
                """SELECT <-triggers_schema<-reflection.text AS reflections
                   FROM schema_pattern WHERE name = $name AND user_id = $user_id""",
                {"name": s["name"], "user_id": user_id},
            )
            s["source_reflections"] = refs[0].get("reflections", []) if refs and not isinstance(refs, str) else []
        return json.dumps(schemas, default=str)

    @tool
    def get_deep_pattern_analysis(pattern_name: str) -> str:
        """Get a deep analysis of a specific pattern — its co-occurring patterns, linked IFS parts, activated schemas, and the actual reflection text where it appeared. Use this when the user asks WHY a pattern exists or wants to understand its roots."""
        refs = conn.query(
            """SELECT <-reveals<-reflection.text AS reflections
               FROM pattern WHERE name = $name AND user_id = $user_id""",
            {"name": pattern_name, "user_id": user_id},
        )
        co = conn.query(
            """SELECT out.name AS co_pattern, count AS times
               FROM co_occurs_with WHERE in.name = $name AND in.user_id = $user_id
               ORDER BY times DESC LIMIT 5""",
            {"name": pattern_name, "user_id": user_id},
        )
        ifs_parts = conn.query(
            """SELECT name, role, description FROM ifs_part
               WHERE <-activates<-reflection->reveals->pattern.name CONTAINS $name AND user_id = $user_id""",
            {"name": pattern_name, "user_id": user_id},
        )
        schemas = conn.query(
            """SELECT name, domain, coping_style, description FROM schema_pattern
               WHERE <-triggers_schema<-reflection->reveals->pattern.name CONTAINS $name AND user_id = $user_id""",
            {"name": pattern_name, "user_id": user_id},
        )
        return json.dumps({
            "pattern": pattern_name,
            "reflections": refs[0].get("reflections", []) if refs and not isinstance(refs, str) else [],
            "co_occurring_patterns": co if co and not isinstance(co, str) else [],
            "linked_ifs_parts": ifs_parts if ifs_parts and not isinstance(ifs_parts, str) else [],
            "linked_schemas": schemas if schemas and not isinstance(schemas, str) else [],
        }, default=str)

    @tool
    def get_people_overview() -> str:
        """Get all people mentioned across reflections — who they are, their relationship to the user, and what patterns they trigger. Use this for questions about relationships, specific people, or interpersonal dynamics."""
        people = conn.query(
            "SELECT name, relationship, description, occurrences FROM person WHERE user_id = $user_id ORDER BY occurrences DESC",
            {"user_id": user_id},
        )
        if not people or isinstance(people, str):
            return "No people identified yet."
        for p in people:
            triggered = conn.query(
                """SELECT ->triggers_pattern->pattern.name AS patterns
                   FROM person WHERE name = $name AND user_id = $user_id""",
                {"name": p["name"], "user_id": user_id},
            )
            p["triggers_patterns"] = triggered[0].get("patterns", []) if triggered and not isinstance(triggered, str) else []
            refs = conn.query(
                """SELECT <-mentions<-reflection.text AS reflections
                   FROM person WHERE name = $name AND user_id = $user_id""",
                {"name": p["name"], "user_id": user_id},
            )
            p["source_reflections"] = refs[0].get("reflections", []) if refs and not isinstance(refs, str) else []
        return json.dumps(people, default=str)

    @tool
    def get_person_deep_dive(person_name: str) -> str:
        """Deep dive into a specific person — what patterns they trigger, what emotions come up around them, what IFS parts activate, and all reflections mentioning them. Use when the user asks about a specific relationship."""
        refs = conn.query(
            """SELECT <-mentions<-reflection.text AS reflections
               FROM person WHERE name = $name AND user_id = $user_id""",
            {"name": person_name, "user_id": user_id},
        )
        patterns = conn.query(
            """SELECT ->triggers_pattern->pattern[*].{name, category} AS patterns
               FROM person WHERE name = $name AND user_id = $user_id""",
            {"name": person_name, "user_id": user_id},
        )
        emotions = conn.query(
            """SELECT ->mentions->person[WHERE name = $name]<-mentions<-reflection->expresses->emotion[*].{name, valence} AS emotions
               FROM person WHERE name = $name AND user_id = $user_id""",
            {"name": person_name, "user_id": user_id},
        )
        return json.dumps({
            "person": person_name,
            "reflections": refs[0].get("reflections", []) if refs and not isinstance(refs, str) else [],
            "patterns_triggered": patterns[0].get("patterns", []) if patterns and not isinstance(patterns, str) else [],
            "emotions": emotions[0].get("emotions", []) if emotions and not isinstance(emotions, str) else [],
        }, default=str)

    @tool
    def get_body_signals_overview() -> str:
        """Get all body signals/somatic markers detected across reflections. Use for questions about physical sensations, body awareness, or somatic patterns."""
        signals = conn.query(
            "SELECT name, location, occurrences FROM body_signal WHERE user_id = $user_id ORDER BY occurrences DESC",
            {"user_id": user_id},
        )
        if not signals or isinstance(signals, str):
            return "No body signals detected yet."
        return json.dumps(signals, default=str)

    @tool
    def hybrid_graph_search(query: str) -> str:
        """Semantic search across ALL graph nodes — patterns, IFS parts, schemas, people, and themes. Finds the most relevant nodes by meaning, then follows graph edges to show connections. Use this when the user's question doesn't match exact node names, or for broad exploratory questions like 'why do I shut down?' or 'what's behind my anxiety?'"""
        query_vec = _embed(query)
        if not query_vec:
            return "Embeddings not available."

        results = {}
        tables = [
            ("pattern", "name, category, description, occurrences"),
            ("ifs_part", "name, role, description, occurrences"),
            ("schema_pattern", "name, domain, coping_style, description, occurrences"),
            ("person", "name, relationship, description, occurrences"),
            ("theme", "name, description"),
        ]
        for table, fields in tables:
            hits = conn.query(
                f"""SELECT {fields}, vector::distance::knn() AS dist
                    FROM {table}
                    WHERE embedding <|3,COSINE|> $vec AND user_id = $user_id
                    ORDER BY dist""",
                {"vec": query_vec, "user_id": user_id},
            )
            if hits and not isinstance(hits, str):
                results[table] = hits

        if results.get("pattern"):
            top_pattern = results["pattern"][0]["name"]
            co = conn.query(
                """SELECT out.name AS co_pattern, count AS times
                   FROM co_occurs_with WHERE in.name = $name AND in.user_id = $user_id
                   ORDER BY times DESC LIMIT 3""",
                {"name": top_pattern, "user_id": user_id},
            )
            results["top_pattern_co_occurs"] = co if co and not isinstance(co, str) else []

        return json.dumps(results, default=str)

    extraction_tools = [retrieve_similar_reflections, get_existing_patterns]
    chat_tools = [
        hybrid_graph_search,
        get_all_patterns_overview,
        get_all_emotions_overview,
        get_ifs_parts_overview,
        get_schemas_overview,
        get_people_overview,
        get_person_deep_dive,
        get_body_signals_overview,
        get_deep_pattern_analysis,
        get_graph_summary,
        get_emotion_triggers,
        get_pattern_connections,
        get_temporal_evolution,
        semantic_search_reflections,
    ]

    return extraction_tools, chat_tools
