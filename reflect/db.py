import os
from dotenv import load_dotenv
from surrealdb import Surreal
from langchain_openai import OpenAIEmbeddings
from langchain_surrealdb.vectorstores import SurrealDBVectorStore
import langchain_surrealdb.vectorstores as vs
from langsmith import traceable

load_dotenv()

EMBEDDING_DIM = 1536

# --- SurrealDB v3 patches ---
vs.DEFINE_INDEX = """
    DEFINE INDEX IF NOT EXISTS {index_name}
        ON TABLE {table}
        FIELDS vector
        HNSW DIMENSION {embedding_dimension} DIST COSINE TYPE F32;
"""

vs.SEARCH_QUERY = """
    SELECT
        id,
        text,
        metadata,
        vector,
        vector::distance::knn() AS similarity
    FROM type::table($table)
    WHERE vector <|{k},COSINE|> $vector
        {custom_filter_str}
    ORDER BY similarity
"""


def get_connection() -> Surreal:
    conn = Surreal(url=os.getenv("SURREAL_URL"))
    conn.use(os.getenv("SURREAL_NS"), os.getenv("SURREAL_DB"))
    conn.signin({"username": os.getenv("SURREAL_USER"), "password": os.getenv("SURREAL_PASS")})
    return conn


def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model="text-embedding-3-small")


def get_vector_store(conn: Surreal, embeddings: OpenAIEmbeddings) -> SurrealDBVectorStore:
    return SurrealDBVectorStore(embeddings, conn, embedding_dimension=EMBEDDING_DIM)


SCHEMA_STATEMENTS = [
    # Node tables
    """DEFINE TABLE reflection SCHEMAFULL""",
    """DEFINE FIELD text ON reflection TYPE string""",
    """DEFINE FIELD created_at ON reflection TYPE datetime DEFAULT time::now()""",
    """DEFINE FIELD daily_prompt ON reflection TYPE option<string>""",
    """DEFINE FIELD source ON reflection TYPE option<string>""",

    """DEFINE TABLE pattern SCHEMAFULL""",
    """DEFINE FIELD name ON pattern TYPE string""",
    """DEFINE FIELD category ON pattern TYPE string""",
    """DEFINE FIELD description ON pattern TYPE string""",
    """DEFINE FIELD occurrences ON pattern TYPE int DEFAULT 1""",
    """DEFINE FIELD first_seen ON pattern TYPE datetime DEFAULT time::now()""",
    """DEFINE FIELD last_seen ON pattern TYPE datetime DEFAULT time::now()""",
    f"""DEFINE FIELD embedding ON pattern TYPE option<array<float>> ASSERT array::len($value) = {EMBEDDING_DIM} OR $value = NONE""",

    """DEFINE TABLE theme SCHEMAFULL""",
    """DEFINE FIELD name ON theme TYPE string""",
    """DEFINE FIELD description ON theme TYPE string""",
    f"""DEFINE FIELD embedding ON theme TYPE option<array<float>> ASSERT array::len($value) = {EMBEDDING_DIM} OR $value = NONE""",

    """DEFINE TABLE emotion SCHEMAFULL""",
    """DEFINE FIELD name ON emotion TYPE string""",
    """DEFINE FIELD valence ON emotion TYPE string""",
    """DEFINE FIELD intensity ON emotion TYPE float""",

    # Edge (relation) tables
    """DEFINE TABLE reveals TYPE RELATION IN reflection OUT pattern""",
    """DEFINE FIELD strength ON reveals TYPE float DEFAULT 1.0""",

    """DEFINE TABLE expresses TYPE RELATION IN reflection OUT emotion""",
    """DEFINE FIELD intensity ON expresses TYPE float""",

    """DEFINE TABLE about TYPE RELATION IN reflection OUT theme""",

    """DEFINE TABLE co_occurs_with TYPE RELATION IN pattern OUT pattern""",
    """DEFINE FIELD count ON co_occurs_with TYPE int DEFAULT 1""",

    """DEFINE TABLE triggered_by TYPE RELATION IN emotion OUT theme""",

    # IFS parts
    """DEFINE TABLE ifs_part SCHEMAFULL""",
    """DEFINE FIELD name ON ifs_part TYPE string""",
    """DEFINE FIELD role ON ifs_part TYPE string""",
    """DEFINE FIELD description ON ifs_part TYPE string""",
    """DEFINE FIELD occurrences ON ifs_part TYPE int DEFAULT 1""",
    """DEFINE FIELD first_seen ON ifs_part TYPE datetime DEFAULT time::now()""",
    """DEFINE FIELD last_seen ON ifs_part TYPE datetime DEFAULT time::now()""",
    f"""DEFINE FIELD embedding ON ifs_part TYPE option<array<float>> ASSERT array::len($value) = {EMBEDDING_DIM} OR $value = NONE""",

    # Schema patterns (Young's Schema Therapy)
    """DEFINE TABLE schema_pattern SCHEMAFULL""",
    """DEFINE FIELD name ON schema_pattern TYPE string""",
    """DEFINE FIELD domain ON schema_pattern TYPE string""",
    """DEFINE FIELD coping_style ON schema_pattern TYPE string""",
    """DEFINE FIELD description ON schema_pattern TYPE string""",
    """DEFINE FIELD occurrences ON schema_pattern TYPE int DEFAULT 1""",
    """DEFINE FIELD first_seen ON schema_pattern TYPE datetime DEFAULT time::now()""",
    """DEFINE FIELD last_seen ON schema_pattern TYPE datetime DEFAULT time::now()""",
    f"""DEFINE FIELD embedding ON schema_pattern TYPE option<array<float>> ASSERT array::len($value) = {EMBEDDING_DIM} OR $value = NONE""",

    # People
    """DEFINE TABLE person SCHEMAFULL""",
    """DEFINE FIELD name ON person TYPE string""",
    """DEFINE FIELD relationship ON person TYPE string""",
    """DEFINE FIELD description ON person TYPE string""",
    """DEFINE FIELD occurrences ON person TYPE int DEFAULT 1""",
    """DEFINE FIELD first_seen ON person TYPE datetime DEFAULT time::now()""",
    """DEFINE FIELD last_seen ON person TYPE datetime DEFAULT time::now()""",
    f"""DEFINE FIELD embedding ON person TYPE option<array<float>> ASSERT array::len($value) = {EMBEDDING_DIM} OR $value = NONE""",

    # Somatic markers
    """DEFINE TABLE body_signal SCHEMAFULL""",
    """DEFINE FIELD name ON body_signal TYPE string""",
    """DEFINE FIELD location ON body_signal TYPE string""",
    """DEFINE FIELD occurrences ON body_signal TYPE int DEFAULT 1""",

    # New edge types
    """DEFINE TABLE activates TYPE RELATION IN reflection OUT ifs_part""",
    """DEFINE TABLE triggers_schema TYPE RELATION IN reflection OUT schema_pattern""",
    """DEFINE TABLE protects_against TYPE RELATION IN ifs_part OUT schema_pattern""",
    """DEFINE TABLE mentions TYPE RELATION IN reflection OUT person""",
    """DEFINE TABLE triggers_pattern TYPE RELATION IN person OUT pattern""",
    """DEFINE TABLE reminds_of TYPE RELATION IN person OUT person""",
    """DEFINE FIELD description ON reminds_of TYPE string""",
    """DEFINE TABLE feels_in_body TYPE RELATION IN reflection OUT body_signal""",

    # ── Multi-user: app_user and reset_token tables ──
    """DEFINE TABLE app_user SCHEMAFULL""",
    """DEFINE FIELD email ON app_user TYPE string""",
    """DEFINE FIELD password_hash ON app_user TYPE string""",
    """DEFINE FIELD telegram_id ON app_user TYPE option<int>""",
    """DEFINE FIELD created_at ON app_user TYPE datetime DEFAULT time::now()""",
    """DEFINE INDEX IF NOT EXISTS app_user_email_idx ON app_user FIELDS email UNIQUE""",
    """DEFINE INDEX IF NOT EXISTS app_user_telegram_idx ON app_user FIELDS telegram_id""",

    """DEFINE TABLE reset_token SCHEMAFULL""",
    """DEFINE FIELD user_id ON reset_token TYPE string""",
    """DEFINE FIELD token ON reset_token TYPE string""",
    """DEFINE FIELD expires_at ON reset_token TYPE datetime""",
    """DEFINE INDEX IF NOT EXISTS reset_token_idx ON reset_token FIELDS token UNIQUE""",

    # ── user_id field on every data table ──
    """DEFINE FIELD user_id ON reflection TYPE option<string>""",
    """DEFINE FIELD user_id ON pattern TYPE option<string>""",
    """DEFINE FIELD user_id ON theme TYPE option<string>""",
    """DEFINE FIELD user_id ON emotion TYPE option<string>""",
    """DEFINE FIELD user_id ON ifs_part TYPE option<string>""",
    """DEFINE FIELD user_id ON schema_pattern TYPE option<string>""",
    """DEFINE FIELD user_id ON person TYPE option<string>""",
    """DEFINE FIELD user_id ON body_signal TYPE option<string>""",

    # HNSW indexes for graph node embeddings
    f"""DEFINE INDEX IF NOT EXISTS pattern_embedding_idx ON pattern FIELDS embedding HNSW DIMENSION {EMBEDDING_DIM} DIST COSINE TYPE F32""",
    f"""DEFINE INDEX IF NOT EXISTS theme_embedding_idx ON theme FIELDS embedding HNSW DIMENSION {EMBEDDING_DIM} DIST COSINE TYPE F32""",
    f"""DEFINE INDEX IF NOT EXISTS ifs_part_embedding_idx ON ifs_part FIELDS embedding HNSW DIMENSION {EMBEDDING_DIM} DIST COSINE TYPE F32""",
    f"""DEFINE INDEX IF NOT EXISTS schema_pattern_embedding_idx ON schema_pattern FIELDS embedding HNSW DIMENSION {EMBEDDING_DIM} DIST COSINE TYPE F32""",
    f"""DEFINE INDEX IF NOT EXISTS person_embedding_idx ON person FIELDS embedding HNSW DIMENSION {EMBEDDING_DIM} DIST COSINE TYPE F32""",
]


@traceable(run_type="tool", name="init_schema")
def init_schema(conn: Surreal):
    for stmt in SCHEMA_STATEMENTS:
        conn.query(stmt)
    print("Schema initialized.")


if __name__ == "__main__":
    conn = get_connection()
    print("Connected to SurrealDB!")
    init_schema(conn)
    vs_ = get_vector_store(conn, get_embeddings())
    print("Vector store ready!")
