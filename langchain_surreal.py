import os
from dotenv import load_dotenv
from surrealdb import Surreal
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_surrealdb.vectorstores import SurrealDBVectorStore
import langchain_surrealdb.vectorstores as vs

load_dotenv()

# --- Patch langchain-surrealdb for SurrealDB v3 compatibility ---
# The langchain-surrealdb package targets v2 syntax. SurrealDB v3 changed:
#   1. MTREE indexes -> HNSW indexes
#   2. KNN operator needs explicit distance metric (e.g. COSINE)
#   3. Can't wrap vector::distance::knn() in expressions like (1 - ...)
EMBEDDING_DIM = 1536  # text-embedding-3-small dimension

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

# --- Step 1: Connect to SurrealDB ---
conn = Surreal(url=os.getenv("SURREAL_URL"))
conn.use(os.getenv("SURREAL_NS"), os.getenv("SURREAL_DB"))
conn.signin({"username": os.getenv("SURREAL_USER"), "password": os.getenv("SURREAL_PASS")})

print("Connected to SurrealDB!")

# --- Step 2: Create the vector store with OpenAI embeddings ---
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vector_store = SurrealDBVectorStore(embeddings, conn, embedding_dimension=EMBEDDING_DIM)

print("Vector store ready!")

# --- Step 3: Add some example documents ---
documents = [
    Document(page_content="SurrealDB is a multi-model database", metadata={"source": "docs"}),
    Document(page_content="LangChain helps build LLM applications", metadata={"source": "docs"}),
    Document(page_content="Vector search finds similar content using embeddings", metadata={"source": "tutorial"}),
]

vector_store.add_documents(documents=documents, ids=["1", "2", "3"])
print(f"Added {len(documents)} documents!")

# --- Step 4: Search for similar content ---
query = "What is SurrealDB?"
results = vector_store.similarity_search_with_score(query=query, k=2)

print(f"\nSearch results for: '{query}'")
for doc, score in results:
    # Note: score is cosine distance (lower = more similar)
    print(f"  [DIST={score:.3f}] {doc.page_content} (source: {doc.metadata.get('source')})")
