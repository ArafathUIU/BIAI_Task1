# Architecture & Workflow Diagrams

Mermaid diagrams describing the Supplier Document Checker (Task 1) pipeline,
component layout, decision precedence, and data flow. Copy any `mermaid` block
into a Mermaid-compatible viewer (GitHub, GitLab, Notion, Obsidian, etc.).

---

## 1. High-level pipeline (fixed-step workflow)

```mermaid
flowchart LR
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:2px
    classDef llm fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef code fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef gate fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    classDef store fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px

    PDF[("Supplier Pack PDF")]
    INGEST[Ingest Document]
    EXTRACT[Extract Quotation]
    VERIFY[Verify Extraction]
    PR[Load Purchase Request]
    COMPARE[Compare Qty / Price]
    RULES[Apply Company Rules]
    DECIDE[Decide / Precedence]
    AUDIT[JSONL Audit]
    UI[Streamlit UI]

    PDF --> INGEST
    INGEST --> EXTRACT
    EXTRACT --> VERIFY
    VERIFY --> PR
    PR --> COMPARE
    COMPARE --> RULES
    RULES --> DECIDE
    DECIDE --> AUDIT
    AUDIT --> UI

    class EXTRACT llm
    class INGEST,VERIFY,PR,COMPARE,RULES,DECIDE code
    class DECIDE gate
    class AUDIT,UI store
```

**Key principle:** `EXTRACT` is the only LLM node. Every decision (Approve / Reject / Needs a person to check) is made by deterministic Python in `RULES` + `DECIDE`. The LLM never decides.

---

## 2. Node-by-node data flow

```mermaid
flowchart TD
    classDef state fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef node fill:#fff,stroke:#333,stroke-width:2px
    classDef gate fill:#fffde7,stroke:#fbc02d,stroke-width:2px

    S1[GraphState raw_text file_hash]
    N1[ingest_document]
    S2[GraphState raw_text ingestion_ok]
    N2[extract_quotation]
    S3[GraphState extraction needs_human]
    N3[verify_extraction]
    S4[GraphState extraction_status ok needs_human]
    N4[apply_pr_comparison]
    S5[GraphState pr_row qty price diffs]
    N5[apply_rules]
    S6[GraphState rule_result]
    N6[decide]
    S7[GraphState final decision reasons]

    S1 --> N1
    N1 --> S2
    S2 --> N2
    N2 --> S3
    S3 --> N3
    N3 --> S4
    S4 --> N4
    N4 --> S5
    S5 --> N5
    N5 --> S6
    S6 --> N6
    N6 --> S7

    class S1,S2,S3,S4,S5,S6,S7 state
    class N1,N2,N3,N4,N5,N6 node
    class N6 gate
```

---

## 3. Decision precedence (the "never guess" gate)

```mermaid
flowchart TD
    classDef reject fill:#ffcdd2,stroke:#b71c1c,stroke-width:2px
    classDef needs fill:#ffe0b2,stroke:#ef6c00,stroke-width:2px
    classDef approve fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    classDef gate fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px

    START[Start verified extraction PR match]
    G1{Extraction OK}
    G2{PR row matched}
    N1[Needs person check uncertain extraction]
    R[apply_rules]
    G3{Any Reject rule}
    G4{Any Needs rule}
    R1[Reject confirmed hard violation]
    N2[Needs person check soft check]
    A[Approve all rules pass]
    END1((Needs human review))
    END2((Reject))
    END3((Needs human review))

    START --> G1
    G1 -->|No| N1
    G1 -->|Yes| G2
    G2 -->|No| N1
    G2 -->|Yes| R
    R --> G3
    G3 -->|Yes| R1
    G3 -->|No| G4
    G4 -->|Yes| N2
    G4 -->|No| A
    N1 --> END1
    R1 --> END2
    N2 --> END3
    A --> END3

    class G1,G2,G3,G4 gate
    class R1 reject
    class N1,N2 needs
    class A approve
    class END1,END2,END3 gate
```

**Precedence rules:**
1. Ingestion failure / no extraction / no PR match → **Needs a person to check**
2. Confirmed Reject rule → **Reject** (wins over soft extraction uncertainty)
3. Critical extraction uncertainty → **Needs a person to check**
4. Otherwise → rule result (Needs or Approve)

---

## 4. Component layout

```mermaid
flowchart TB
    classDef data fill:#ff9900,stroke:#000,stroke-width:2px,color:#fff
    classDef py fill:#3776ab,stroke:#000,stroke-width:2px,color:#fff
    classDef ui fill:#ff4b4b,stroke:#000,stroke-width:2px,color:#fff
    classDef store fill:#2ecc71,stroke:#000,stroke-width:2px,color:#fff

    subgraph data_layer[Sample Data]
        PR[purchase-request.csv]
        RULES[company-rules.md]
        PACKS[supplier-pack-01..10.pdf]
    end

    subgraph src_layer[src/supplier_check]
        INGEST[ingest.py]
        EXTRACT[extract.py + prompt]
        VERIFY[verify.py + clauses.py]
        PRMOD[pr.py]
        RULES_ENGINE[rules.py]
        DECIDE[decide.py]
        GRAPH[graph.py LangGraph StateGraph]
        STORE[store.py JSONL audit]
        UI[ui.py + control_center]
    end

    subgraph audit_store[Audit Output]
        RUNS[runs timestamp results.jsonl]
        WORKSPACE[workspace live Control Center docs]
    end

    subgraph streamlit[Streamlit UI]
        APP[app.py navigation]
        PAGES[pages Overview New Verification Documents Evaluation Detail]
        COMPS[components HTML tables badges charts]
        CSS[styles.py CSS design tokens]
    end

    PR --> PRMOD
    RULES --> RULES_ENGINE
    PACKS --> INGEST
    INGEST --> EXTRACT
    EXTRACT --> VERIFY
    VERIFY --> PRMOD
    PRMOD --> RULES_ENGINE
    RULES_ENGINE --> DECIDE
    DECIDE --> GRAPH
    GRAPH --> STORE
    STORE --> RUNS
    GRAPH --> UI
    UI --> APP
    APP --> PAGES
    PAGES --> COMPS
    COMPS --> CSS
    WORKSPACE -.-> RUNS

    class data_layer,data data
    class src_layer,py
    class streamlit,ui
    class audit_store,store
```

---

## 5. Verification gates (evidence + arithmetic)

```mermaid
flowchart TD
    classDef gate fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    classDef pass fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    classDef fail fill:#ffcdd2,stroke:#b71c1c,stroke-width:2px

    EXT[LLM Extraction value evidence confidence]
    G1{Required fields present}
    G2{Evidence quote is substring of raw text}
    G3{Percent fields match evidence percent tokens}
    G4{Arithmetic qty price line subtotal VAT total}
    F1[needs human missing required field]
    F2[needs human field unverified]
    F3[needs human UNCERTAIN normalized]
    F4[Note arithmetic mismatch recorded for rules]
    OK[extraction status ok]

    EXT --> G1
    G1 -->|No| F1
    G1 -->|Yes| G2
    G2 -->|No| F2
    G2 -->|Yes| G3
    G3 -->|No| F3
    G3 -->|Yes| G4
    G4 -->|No| F4
    G4 -->|Yes| OK

    class G1,G2,G3,G4 gate
    class F1,F2,F3,F4 fail
    class OK pass
```

---

## 6. Provider resolution (LLM adapter)

```mermaid
flowchart TD
    classDef provider fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef default fill:#f9f9f9,stroke:#333,stroke-width:2px

    ENV[.env environment variables]
    G1{LLM_BASE_URL set}
    G2{GROQ_API_KEY set}
    G3{OPENAI_API_KEY set}
    P1[Ollama custom endpoint model LLM_MODEL]
    P2[Groq API model GROQ_MODEL]
    P3[OpenAI API model LLM_MODEL]
    ERR[RuntimeError no credentials]

    ENV --> G1
    G1 -->|Yes| P1
    G1 -->|No| G2
    G2 -->|Yes| P2
    G2 -->|No| G3
    G3 -->|Yes| P3
    G3 -->|No| ERR

    class P1,P2,P3 provider
    class ERR default
```

**Precedence:** `LLM_BASE_URL` → `GROQ_API_KEY` → `OPENAI_API_KEY`. Temperature is always `0`.

---

## 7. Golden labels (acceptance target)

```mermaid
flowchart LR
    classDef approve fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    classDef reject fill:#ffcdd2,stroke:#b71c1c,stroke-width:2px
    classDef needs fill:#ffe0b2,stroke:#ef6c00,stroke-width:2px

    P01[Pack 01 Padma Textile Item A]
    P02[Pack 02 Jamuna Trims Item B]
    P03[Pack 03 Karnaphuli Yarn Item C]
    P04[Pack 04 Surma Packaging Item D]
    P05[Pack 05 Meghna Carton Item E]
    P06[Pack 06 Teesta Fabrics Item A]
    P07[Pack 07 Rupsha Zipper Item B]
    P08[Pack 08 Bhairab Thread Item C]
    P09[Pack 09 Dhaleshwari Poly Item D]
    P10[Pack 10 Kushiyara Box Item E]

    A1[Approve]
    A2[Approve]
    R1[Reject price over 3 percent]
    N1[Needs price under 3 percent]
    R2[Reject advance 40 percent]
    R3[Reject no penalty clause]
    N2[Needs quantity minus 17.5 percent]
    R4[Reject TIN BIN missing]
    N3[Needs payment plus math mismatch]
    R5[Reject delivery 60 days VAT]

    P01 --> A1
    P02 --> A2
    P03 --> R1
    P04 --> N1
    P05 --> R2
    P06 --> R3
    P07 --> N2
    P08 --> R4
    P09 --> N3
    P10 --> R5

    Tally[2 Approve 5 Reject 3 Needs]

    class A1,A2 approve
    class R1,R2,R3,R4,R5 reject
    class N1,N2,N3 needs
```

---

## How to read these diagrams

- **Fixed steps:** The pipeline is a linear `StateGraph`. There are no tool-calling loops and no autonomous agent.
- **LLM boundary:** The LLM touches data only in the `extract` node. Every business decision is deterministic Python.
- **Audit trail:** Every run writes `runs/<timestamp>/results.jsonl` with the model used, prompt hash, decision, reasons, and evidence quotes.
- **Evaluation:** The Control Center Evaluation page runs the 10 sample packs against locked golden labels in `tests/fixtures/expected.json`.