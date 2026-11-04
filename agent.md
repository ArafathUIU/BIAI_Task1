# agent.md - Cursor Agent Guide for Task 1 Supplier Document Checker

This file tells a Cursor (or any coding) agent how to implement and maintain the
project described in `PLAN.md`. Treat `PLAN.md` as the source of truth for
architecture and scope. If you change architecture, update `PLAN.md` in the same
commit/PR.

## 0. Mission

Implement a **fixed-step LangGraph pipeline** that checks 10 supplier packs and
produces Approve / Reject / Needs a person to check with exact evidence. Never
guess: uncertain extractions must stop for human review. Do not build a
free-running agent with tools.

## 1. Repository layout (target)

```text
supplier-doc-check/
  pyproject.toml
  uv.lock
  .env.example
  README.md
  agent.md                 # copy of this file at repo root
  PLAN.md
  prompts/
    extract_quotation.md
  src/supplier_check/
    __init__.py
    config.py
    schemas.py
    ingest.py
    extract.py
    verify.py
    pr.py
    rules.py
    decide.py
    graph.py
    store.py              # JSONL audit; SQLite optional post-MVP
    ui.py
  tests/
    test_golden_labels.py
    test_rule_engine.py
    test_extraction_schema.py
    test_arithmetic.py
    test_pr_match.py
    fixtures/expected.json
  data/
    purchase-request.csv
    company-rules.md
    supplier-pack-*.pdf
  runs/                   # timestamped JSONL outputs (gitignored contents)
  reports/
    evaluation.md
```

## 2. Non-negotiable rules for the agent

1. **No free-running agent.** Only a `StateGraph` with named nodes and explicit
   edges. No tool-calling loops, no autonomous planning.
2. **LLM is extraction-only.** Decisions come from pure Python in `rules.py`.
   Do not let the LLM decide approve/reject.
3. **Never guess.** If extraction is uncertain, write "Needs a person to check".
   Never auto-approve uncertain data.
4. **Evidence beats confidence.** Required gates are schema validity, evidence
   substring of source text, and arithmetic checks. LLM self-confidence is a weak
   secondary signal only — never treat high confidence as proof if evidence fails.
5. **Determinism.** Temperature 0, versioned prompts, hashed inputs in audit log.
6. **Do not edit golden labels** in `tests/fixtures/expected.json` to make tests
   pass. If a label seems wrong, update `PLAN.md` section 3 and section 7 together
   and explain in the PR.
7. **Secrets.** Read API keys from env only. Never commit `.env`. `.env.example`
   must contain placeholders only, and must document OpenAI, Groq, and Ollama.
8. **Respect the MVP cut line** in `PLAN.md` §4.1. Do not build live HITL
   interrupt, SQLite, LangSmith, Docker, or OCR before golden labels + Streamlit
   batch/detail UI are done.
9. **Small, reviewable changes.** One phase per PR/commit where possible.

## 3. Environment and commands

```bash
cd supplier-doc-check
cp .env.example .env        # fill ONE of: OPENAI_API_KEY / GROQ_API_KEY / LLM_BASE_URL
uv sync
uv run python -m pytest     # all tests
uv run streamlit run src/supplier_check/ui.py
uv run python -m supplier_check.graph --input data/ --out runs/
```

Required env vars (`.env.example`) — precedence: `LLM_BASE_URL` → `GROQ_API_KEY` → `OPENAI_API_KEY`:
- `OPENAI_API_KEY=` + `LLM_MODEL=gpt-4o-mini`
- `GROQ_API_KEY=` + `GROQ_MODEL=llama-3.3-70b-versatile`
- `LLM_BASE_URL=` (e.g. `http://localhost:11434/v1`) + `LLM_MODEL=` + optional `LLM_API_KEY=`
- `LLM_TEMPERATURE=0`
- `CONFIDENCE_THRESHOLD=0.80` (soft secondary gate only)
- `LANGSMITH_API_KEY=` (optional; skip for MVP)

## 4. Coding standards

- Python 3.11+, type hints everywhere, Pydantic v2 models in `schemas.py`.
- `ruff` for lint/format; line length 100.
- Functions small and single-purpose; one node per file where practical.
- Money as `Decimal`, never float, for rule comparisons; convert at boundaries.
- All external I/O (PDF, LLM, DB) behind functions with clear inputs/outputs so
  tests can mock them.
- No global state; pass `GraphState` through nodes.
- Log with `logging`, not `print`, except CLI user-facing output.

## 5. Implementation checklist (follow phases in PLAN.md)

MVP (do these first, in order):
- [ ] Phase 1: scaffold + `uv sync` + empty pytest green
- [ ] Phase 2: PDF ingestion + Pydantic schemas + prompt file
- [ ] Phase 3: LLM extraction node, all 10 parse
- [ ] Phase 4: verification (evidence substring + arithmetic primary; confidence soft)
- [ ] Phase 5: PR comparison + rule engine; golden labels pass
- [ ] Phase 6: decision precedence + JSONL audit (soft Needs gate, no live interrupt)
- [ ] Phase 7: Streamlit UI (batch, table, detail/evidence)
- [ ] Phase 8: tests + `reports/evaluation.md`
- [ ] Phase 9: README + one-page note + Loom script

Optional only after MVP is green:
- [ ] Phase 6b: live HITL interrupt + SQLite review queue
- [ ] Phase 10: OCR / Docker / LangSmith / concurrency

Do not skip Phase 5 tests before moving to UI.
Do not start optional work before Phases 7–9 are usable.

## 6. Testing requirements

Minimum tests the agent must add and keep green:
- `test_golden_labels.py`: decision + primary reason for all 10 packs.
- `test_rule_engine.py`: boundary values for price (+3.0 exactly), quantity (+/-5.0
  exactly), delivery (45, 31, 30, 46), payment (30, 60), validity (30, 29);
  **and** `delivery_days=None` -> Needs (not Reject); `delivery_days=60` -> Reject.
- `test_extraction_schema.py`: required fields, evidence substring verification;
  confidence is optional/soft.
- `test_arithmetic.py`: `qty * unit_price`, subtotal, 15% VAT, total.
- `test_pr_match.py`: item lookup and missing-row handling.

When adding a rule, add at least one positive and one negative test.

## 7. Data and file handling

- Sample data lives in `data/` (copy from the supplied pack). Do not modify the
  original sample files.
- Treat PDFs as read-only inputs.
- Cache extracted text by sha256 to avoid repeated work; cache key includes file hash.
- Write outputs to `runs/<timestamp>/`, never overwrite prior runs.

## 8. UI expectations

Streamlit app must allow a non-technical reviewer to:
1. Run all 10 packs in one click.
2. See a results table: doc, supplier, item, qty diff %, price diff %, decision, reason.
3. Open a detail view with raw text, extracted fields, evidence quotes, rule hits.

Optional (post-MVP): a review-queue form for uncertain/Needs records.

No login required for the demo.

## 9. Review criteria (what the human reviewer will check)

- Loom: clear, confident, explains why, non-technical followable.
- Accuracy: 10/10 decisions on sample files.
- Design: fixed steps, handles mistakes, never guesses.
- Hardest part: uncertainty handling quality.
- Code: clean, runnable from README.
- Honesty: limitations stated clearly.

## 10. Definition of done

A change is done when:
- `uv run pytest` is green.
- `uv run ruff check .` is clean.
- README instructions reproduce the result on a fresh machine.
- Golden labels still match (or PLAN.md updated with justification).
- No secrets committed.
- `reports/evaluation.md` regenerated if metrics changed.

## 11. When stuck

- If a PDF field is ambiguous, do not invent a value. Fail evidence/schema checks
  and write "Needs a person to check".
- If the LLM output fails schema validation, retry once with the validation error
  appended; if it fails again, route to Needs / human review.
- If a rule is unclear, prefer "Needs a person to check" over "Reject" or "Approve".
- Missing delivery days -> Needs, not Reject. Reject delivery only when days > 45.
- Ask the user before changing scope, golden labels, decision precedence, or the
  MVP cut line in `PLAN.md` §4.1.