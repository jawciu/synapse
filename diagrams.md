# Synapse — Mermaid Diagrams

## Scenario 1: Reflection Pipeline

```mermaid
graph TD
    A[User submits reflection] --> B[store_reflection<br/><i>~0.2s</i>]
    A --> C[extract_patterns<br/><i>~12s — Agentic RAG</i>]

    B --> D[update_graph<br/><i>~0.5s</i>]
    C --> D

    D --> E[query_graph<br/><i>~0.3s</i>]
    E --> F[generate_insights<br/><i>~4s</i>]
    F --> G[generate_followups<br/><i>~3s</i>]
    G --> H[Response to user]

    style A fill:#4a9eff,color:#fff
    style B fill:#2d8659,color:#fff
    style C fill:#c44dff,color:#fff
    style D fill:#2d8659,color:#fff
    style E fill:#2d8659,color:#fff
    style F fill:#e6a817,color:#fff
    style G fill:#e6a817,color:#fff
    style H fill:#4a9eff,color:#fff
```

## Extraction Agent — Agentic RAG Loop

```mermaid
sequenceDiagram
    participant P as Pipeline
    participant LLM as GPT-4o
    participant T as Tools (SurrealDB)

    P->>LLM: Analyze this reflection
    Note over LLM: "I should check<br/>what exists first"

    LLM->>T: search_existing_patterns()
    T-->>LLM: 3 similar patterns found

    LLM->>T: search_similar_reflections()
    T-->>LLM: 2 past reflections match

    Note over LLM: "Found matches,<br/>let me check full list"

    LLM->>T: get_all_patterns()
    T-->>LLM: 16 patterns in DB

    Note over LLM: "Now I have context.<br/>Reuse existing names,<br/>extract new ones."

    LLM-->>P: Structured JSON output:<br/>patterns, emotions, IFS parts,<br/>schemas, people, body signals
```

## Scenario 2: Chat Agent — ReAct Loop

```mermaid
graph TD
    A[User asks a question] --> B{ReAct Agent<br/>GPT-4o}

    B -->|decides tool| C[Tool Call #1]
    C --> D{Need more info?}
    D -->|yes| E[Tool Call #2]
    E --> F{Need more info?}
    F -->|yes| G[Tool Call #3]
    F -->|no| H[Generate answer]
    D -->|no| H
    G --> H
    H --> I[Grounded response<br/>to user]

    style A fill:#4a9eff,color:#fff
    style B fill:#c44dff,color:#fff
    style C fill:#2d8659,color:#fff
    style E fill:#2d8659,color:#fff
    style G fill:#2d8659,color:#fff
    style H fill:#e6a817,color:#fff
    style I fill:#4a9eff,color:#fff
```

## Chat Agent — 14 Available Tools

```mermaid
graph LR
    Agent((ReAct<br/>Chat Agent))

    Agent --> P1[get_all_patterns]
    Agent --> P2[get_pattern_detail]
    Agent --> P3[get_central_patterns]
    Agent --> P4[get_co_occurrences]
    Agent --> P5[get_negative_triggers]
    Agent --> P6[get_emotions_overview]
    Agent --> P7[get_ifs_parts_overview]
    Agent --> P8[get_schemas_overview]
    Agent --> P9[get_deep_pattern_analysis]
    Agent --> P10[get_people_overview]
    Agent --> P11[get_person_deep_dive]
    Agent --> P12[get_body_signals_overview]
    Agent --> P13[search_similar_reflections]
    Agent --> P14[hybrid_graph_search]

    style Agent fill:#c44dff,color:#fff
    style P1 fill:#2d8659,color:#fff
    style P2 fill:#2d8659,color:#fff
    style P3 fill:#2d8659,color:#fff
    style P4 fill:#2d8659,color:#fff
    style P5 fill:#2d8659,color:#fff
    style P6 fill:#2d8659,color:#fff
    style P7 fill:#e6a817,color:#fff
    style P8 fill:#e6a817,color:#fff
    style P9 fill:#e6a817,color:#fff
    style P10 fill:#4a9eff,color:#fff
    style P11 fill:#4a9eff,color:#fff
    style P12 fill:#4a9eff,color:#fff
    style P13 fill:#c44dff,color:#fff
    style P14 fill:#c44dff,color:#fff
```

## Knowledge Graph Schema

```mermaid
graph TD
    R[reflection] -->|reveals| P[pattern]
    R -->|expresses| EM[emotion]
    R -->|about| TH[theme]
    R -->|activates| IFS[ifs_part]
    R -->|triggers_schema| SC[schema_pattern]
    R -->|mentions| PE[person]
    R -->|feels_in_body| BS[body_signal]

    P <-->|co_occurs_with| P
    EM -->|triggered_by| TH
    IFS -->|protects_against| SC
    PE -->|triggers_pattern| P
    PE -->|reminds_of| PE

    style R fill:#4a9eff,color:#fff
    style P fill:#c44dff,color:#fff
    style EM fill:#e6a817,color:#fff
    style TH fill:#2d8659,color:#fff
    style IFS fill:#ff6b6b,color:#fff
    style SC fill:#ff6b6b,color:#fff
    style PE fill:#4a9eff,color:#fff
    style BS fill:#e6a817,color:#fff
```

## Hybrid Search — Vector + Graph

```mermaid
graph LR
    Q[User query:<br/>'abandonment'] --> VS[Vector Search<br/>KNN across all nodes]
    Q --> GS[Graph Traversal<br/>Follow edges]

    VS --> P1[pattern:<br/>fear of abandonment<br/><i>similarity: 0.92</i>]
    VS --> S1[schema:<br/>abandonment/instability<br/><i>similarity: 0.89</i>]
    VS --> I1[ifs_part:<br/>wounded child<br/><i>similarity: 0.85</i>]

    GS --> P2[pattern: fear of abandonment<br/>->co_occurs_with-><br/>emotional dysregulation]
    GS --> PE[person: Dad<br/>->triggers_pattern-><br/>fear of abandonment]

    P1 --> R[Combined<br/>results]
    S1 --> R
    I1 --> R
    P2 --> R
    PE --> R

    style Q fill:#4a9eff,color:#fff
    style VS fill:#c44dff,color:#fff
    style GS fill:#2d8659,color:#fff
    style R fill:#e6a817,color:#fff
```

## Full System Overview

```mermaid
graph TB
    subgraph User Interface
        UI[Streamlit / TypeScript App]
    end

    subgraph Reflection Pipeline
        RP[LangGraph StateGraph<br/>6 nodes, parallel entry]
    end

    subgraph Chat Agent
        CA[LangGraph ReAct Agent<br/>14 tools]
    end

    subgraph Extraction Agent
        EA[LangGraph ReAct Agent<br/>Agentic RAG]
    end

    subgraph SurrealDB v3 Cloud
        GDB[(Graph Database<br/>7 node types<br/>11 edge types)]
        VDB[(Vector Store<br/>HNSW indexes<br/>1536d embeddings)]
    end

    subgraph Observability
        LS[LangSmith<br/>Full trace on every node]
    end

    UI -->|submit reflection| RP
    UI -->|ask question| CA
    RP --> EA
    RP --> GDB
    RP --> VDB
    CA --> GDB
    CA --> VDB
    EA --> GDB
    EA --> VDB
    RP -.->|@traceable| LS
    CA -.->|@traceable| LS
    EA -.->|@traceable| LS

    style UI fill:#4a9eff,color:#fff
    style RP fill:#c44dff,color:#fff
    style CA fill:#c44dff,color:#fff
    style EA fill:#c44dff,color:#fff
    style GDB fill:#2d8659,color:#fff
    style VDB fill:#2d8659,color:#fff
    style LS fill:#e6a817,color:#fff
```
