# Supplier Document Checker (Task 1)

## Problem statement

A garment company (Aamar Garments Ltd) receives supplier quotations and contracts
as PDF documents. Each pack contains a quotation plus terms and conditions for one
purchase-request item. The company needs an AI system that:

1. **Reads** each supplier quote and pulls out supplier name, items, quantities,
   prices, delivery date, payment terms, VAT, TIN/BIN, validity, and penalty clauses.
2. **Compares** the quote against the company's purchase request and flags wrong
   quantity or price.
3. **Checks** the contract against company rules (payment terms, VAT, late-delivery
   penalty, TIN/BIN, delivery window).
4. **Decides** per document: **Approve**, **Reject**, or **Needs a person to check**,
   with the exact reason.
5. **Never guesses** — when unsure, it stops and asks a person.

The brief explicitly requires **clear fixed steps** (e.g. LangGraph), not one
free-running agent.

---

## Goal and approach

### Goal

Build a deterministic, auditable pipeline that checks all 10 sample supplier packs
and reproduces the correct decision (Approve / Reject / Needs a person to check)
for every one — targeting 10/10 accuracy on the golden dataset.

### Approach

- **LLM is extraction-only:** The language model extracts structured fields +
  evidence quotes from each PDF. It never decides approve/reject.
- **Decisions are deterministic Python:** A pure rule engine applies every company
  rule. The same input always produces the same decision (temperature 0, fixed
  prompts).
- **Never guess:** Missing fields, unverifiable evidence, or arithmetic mismatches
  route to "Needs a person to check" instead of a confident wrong answer.
- **Fixed-step workflow:** Implemented as a LangGraph `StateGraph` with explicit
  nodes and edges — no tool-calling agent loop.
- **Evidence-backed:** Every decision carries the exact source text that supports it.
- **Runnable by a reviewer:** One-command setup with `uv`, plus a Streamlit demo UI.

---

## Project structure

```text
BIAI_Task2/
├── README.md                 # This file
├── ARCHITECTURE.md           # Mermaid workflow + component diagrams
├── PLAN.md                   # Phase-by-phase implementation plan
├── Decisions.md              # Recorded architectural decisions (D0-D22)
├── agent.md                  # Cursor agent conventions and checklist
├── pyproject.toml            # Project config, dependencies, pytest/ruff
├── .env.example              # Environment template (never commit .env)
├── .streamlit/config.toml    # Streamlit server settings (port 8510)
├── data/                     # Sample files (read-only)
│   ├── purchase-request.csv
│   ├── company-rules.md
│   └── supplier-pack-01.pdf .. supplier-pack-10.pdf
├── prompts/                  # Versioned LLM prompts
│   └── extract_quotation.md
├── src/supplier_check/       # Python package
│   ├── __init__.py
│   ├── config.py             # Env-driven configuration
│   ├── schemas.py            # Pydantic v2 models (GraphState, extraction)
│   ├── ingest.py             # PDF text extraction (pdfplumber + pypdf)
│   ├── extract.py            # LLM extraction node (Groq/OpenAI/Ollama)
│   ├── verify.py             # Evidence + arithmetic + % reconciliation
│   ├── clauses.py            # Deterministic late-penalty clause scanner
│   ├── pr.py                 # Purchase-request loading + comparison
│   ├── rules.py              # Deterministic company rule engine
│   ├── decide.py             # Decision precedence (Reject beats uncertainty)
│   ├── graph.py              # LangGraph StateGraph wiring + batch runner
│   ├── store.py              # JSONL audit writer
│   └── ui.py                 # Streamlit demo entry point
├── src/supplier_check/control_center/   # Streamlit Control Center UI
│   ├── app.py                # Navigation + KPI sidebar
│   ├── workspace.py          # Live document persistence (JSON files)
│   ├── processing.py         # Sequential pipeline invocation
│   ├── session.py            # Session-state helpers
│   ├── styles.py             # CSS design tokens
│   ├── components.py         # HTML tables, badges, charts, reason panels
│   └── pages/                # Overview / New Verification / Documents / Evaluation / Detail
├── tests/                    # pytest suite (59 tests)
│   ├── test_golden_labels.py # Locked 10-pack decisions vs expected.json
│   ├── test_rules.py         # Rule engine unit tests + boundaries
│   ├── test_verify.py        # Verification gate tests
│   ├── test_extract.py       # Extraction node + provider selection tests
│   ├── test_graph.py         # End-to-end graph + batch resilience tests
│   ├── test_pr_match.py      # Purchase-request loader tests
│   ├── test_decide.py        # Decision precedence tests
│   ├── test_clauses.py       # Late-penalty scanner tests
│   ├── test_percent_reconcile.py   # D21 percent reconciliation tests
│   ├── test_ui.py            # UI helper tests
│   ├── test_workspace.py     # Live workspace persistence tests
│   ├── test_schemas.py       # Pydantic schema tests
│   └── fixtures/expected.json    # Locked golden labels
├── runs/                     # JSONL audit output (gitignored)
├── workspace/                # Control Center live docs (gitignored)
└── reports/                  # Evaluation report
```

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Best ecosystem for PDF, LLM, and workflow tooling |
| Workflow engine | LangGraph `StateGraph` | Named in the brief; fixed nodes/edges; no free-running agent |
| Schemas | Pydantic v2 | Single contract for extraction, state, and audit; strict validation |
| LLM access | `openai` SDK adapter | Works with OpenAI, Groq, or Ollama via `LLM_BASE_URL` |
| Providers | OpenAI / Groq / Ollama | Precedence: `LLM_BASE_URL` → `GROQ_API_KEY` → `OPENAI_API_KEY` |
| PDF text | `pdfplumber` → `pypdf` fallback | Table-aware extraction with a no-dependency fallback |
| UI | Streamlit | Fastest credible demo for a non-technical reviewer |
| Audit | JSONL (`runs/<timestamp>/results.jsonl`) | Zero-setup, human-readable, diffable |
| Packaging | `uv` + `pyproject.toml` | Reproducible installs; one-command setup |
| Tests | `pytest` + `ruff` | 59 tests; clean lint |

**Key decision:** The LLM is used **only for extraction + evidence quoting**. All
approve/reject/needs decisions are made by deterministic Python in `rules.py`.
This makes results reproducible, auditable, and defensible — and directly satisfies
the "never guesses" requirement.

---
