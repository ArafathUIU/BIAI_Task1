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

## How to run (step by step)

### Step 1: Clone and enter the project

```bash
git clone https://github.com/ArafathUIU/BIAI_Task2.git
cd BIAI_Task2
```

### Step 2: Install dependencies

```bash
uv sync
```

This creates a virtual environment and installs all runtime + dev dependencies.

### Step 3: Configure your LLM provider

Copy the template and fill in **one** provider:

```bash
cp .env.example .env
```

Then edit `.env` and set one of:

| Provider | Required env var | Example |
|---|---|---|
| Groq | `GROQ_API_KEY` | `GROQ_API_KEY=gsk_...` |
| OpenAI | `OPENAI_API_KEY` | `OPENAI_API_KEY=sk-...` |
| Ollama / custom | `LLM_BASE_URL` | `LLM_BASE_URL=http://localhost:11434/v1` |

Provider precedence: `LLM_BASE_URL` → `GROQ_API_KEY` → `OPENAI_API_KEY`.

Never commit `.env` — it is gitignored and contains your secret key.

### Step 4: Run the test suite

```bash
uv run python -m pytest
uv run ruff check .
```

Expect all tests green (59 tests) and ruff clean.

### Step 5: Run the batch pipeline on the 10 sample packs

```bash
uv run python -m supplier_check.graph --input data/ --out runs/
```

This processes each PDF through the fixed LangGraph pipeline and writes one JSONL
audit record per document under `runs/<timestamp>/results.jsonl`.

### Step 6: Launch the Streamlit demo UI

```bash
uv run streamlit run src/supplier_check/ui.py
```

Open `http://localhost:8510` (port set in `.streamlit/config.toml`). The UI lets
you:

- Upload and process one or many supplier PDFs (New Verification)
- View KPIs and decision distribution (Overview)
- Browse All / Approved / Rejected / Needs Human Review documents
- Open a document detail with extraction fields, evidence quotes, and rule hits
- Run the golden-label Evaluation against the 10 sample packs

---

## Scoring mapping (brief criteria)

| Brief criterion | Weight | How this project addresses it |
|---|---:|---|
| Loom presentation | 20% | UI detail view shows exact source quotes supporting each decision; fixed steps are easy to explain |
| Works on sample files | 25% | 59 tests including golden-label lock targeting 10/10 decisions |
| Clear, sensible build, handles mistakes | 20% | Fixed LangGraph nodes, conservative "Needs" gate, evidence + arithmetic gates |
| Hardest part (never guess) | 15% | Evidence substring + arithmetic + percent reconciliation; never auto-approve |
| Clean runnable code | 10% | `uv sync` one-liner, pytest + ruff green, `.env.example` for OpenAI/Groq/Ollama |
| Honesty | 10% | Limitations documented below; evaluation report separate from live UI |

### Loom presentation outline

1. **Problem** (30s): What the garment company needs — check supplier quotes against a purchase request and company rules, never guess.
2. **Approach** (45s): Fixed-step LangGraph pipeline; LLM extracts, Python rules decide; evidence-backed decisions.
3. **Demo** (2min): Run the batch pipeline on all 10 packs; show the Streamlit UI with the results table and a document detail view highlighting the exact quote behind each decision.
4. **Why these choices** (45s): Extraction-only LLM + deterministic rules = reproducible, auditable, no hallucinated decisions.
5. **Limitations** (30s): Text-based PDFs only; no OCR; small models via Ollama may reduce extraction quality; honest about what the system does not do.

---

## Known limitations

- Text-based PDFs only; scanned/image PDFs are not handled in v1 (OCR is future work).
- Bangla text is not supported (not needed for Task 1).
- Payment-term parsing is heuristic; complex multi-clause terms may need human review.
- VAT-inclusive quotes are not reverse-engineered into ex-VAT unit prices; Pack 10 rejects on delivery >45 days, with VAT-not-separate as an additional rule hit.
- Small models via Ollama may reduce extraction quality; OpenAI/Groq recommended for the scored demo.
- The system does not send emails or update an ERP; it produces a decision + audit record.

---
