# Plan: Task 1 - Supplier Document Checker (Aamar Garments Ltd)

## 1. Task in one paragraph

Build a **deterministic, step-by-step AI pipeline** that reads each of the 10 supplier
packs (one quotation + terms and conditions per PDF), extracts the commercial fields,
compares them against `purchase-request.csv`, applies the company rules in
`company-rules.md`, and returns one of **Approve / Reject / Needs a person to check**
with the exact document text that supports the decision. The hardest part is
"never guess": missing, low-confidence, or inconsistent extractions must stop and
ask a human instead of producing a confident wrong answer. The brief explicitly
forbids a free-running agent; this must be a fixed workflow (LangGraph).

## 2. Sample data we are working with

Location: `BIAI-AI-Engineer-Round2-Pack/sample-data/engineer/task1-procurement/`

| File | Purpose |
|---|---|
| `purchase-request.csv` | PR-2026-114, 5 items (A-E), requested qty + max unit price |
| `company-rules.md` | Reject / Needs / Approve rules + notes |
| `supplier-pack-01.pdf` .. `supplier-pack-10.pdf` | One quotation + T&C per pack, one item each |

Purchase request summary:

| Item | Description | Unit | Qty requested | Max unit price (BDT) |
|---|---|---|---:|---:|
| A | Cotton twill fabric, 280 gsm | metre | 12,000 | 480.00 |
| B | Metal zipper, 18 cm | piece | 20,000 | 38.00 |
| C | Polyester sewing thread, cone | cone | 800 | 210.00 |
| D | Poly bag, 30 x 40 cm | piece | 50,000 | 6.50 |
| E | Carton box, 5-ply | piece | 3,000 | 95.00 |

## 3. Expected decisions on the 10 packs (golden labels for testing)

These are derived by applying the rules manually. They are the acceptance target:
the system must match all 10.

| Pack | Supplier | Item | Qty | Unit price | Decision | Primary reason |
|---:|---|---|---:|---:|---|---|
| 01 | Padma Textile Mills Ltd | A | 12,000 | 472.00 | **Approve** | All rules pass |
| 02 | Jamuna Trims and Accessories | B | 20,000 | 36.00 | **Approve** | All rules pass |
| 03 | Karnaphuli Yarn Traders | C | 800 | 229.00 | **Reject** | Unit price 9.05% above max (>3%) |
| 04 | Surma Packaging Industries | D | 50,000 | 6.65 | **Needs person** | Unit price 2.31% above max (<=3%) |
| 05 | Meghna Carton Works | E | 3,000 | 92.00 | **Reject** | Advance payment 40% (>20%) |
| 06 | Teesta Fabrics Ltd | A | 12,000 | 465.00 | **Reject** | No late-delivery penalty clause |
| 07 | Rupsha Zipper Factory | B | 16,500 | 35.00 | **Needs person** | Quantity 17.5% below requested (>5%) |
| 08 | Bhairab Thread and Co | C | 800 | 205.00 | **Reject** | TIN/BIN missing |
| 09 | Dhaleshwari Poly Pack | D | 50,000 | 6.40 | **Needs person** | Payment terms unclear (30-90 days) AND line total mismatch (6.40 x 50,000 = 320,000 != 322,000) |
| 10 | Kushiyara Box Industries | E | 3,000 | 94.00 (VAT incl.) | **Reject** | Delivery 60 days (>45); VAT not shown separately |

Tally: Approve 2, Reject 5, Needs a person 3.

Edge cases the rule engine must handle explicitly:

- Boundary values: price exactly +3.00%, quantity exactly +/-5%, delivery exactly 45 days,
  payment exactly 30/60 days, validity exactly 30 days. Rule text uses "more than" /
  "less than", so boundaries go to the softer bucket.
- Unit conversion: "4 weeks" must become 28 days; "60 days" stays 60.
- Missing / unparseable delivery days -> **Needs a person**, never Reject. Reject only
  when a numeric delivery promise exists and is `> 45`.
- VAT-inclusive pricing (pack 10): Reject on delivery 60 days. Do not invent an
  ex-VAT unit price. Also record "VAT not shown separately" as a rule hit.
- Arithmetic tolerance: compare money with a 0.01 BDT tolerance.
- Missing TIN/BIN phrased as "registration details available on request" must be
  treated as missing.

## 4. Goals and non-goals

Goals:
- Deterministic decisions that reproduce on every run (temperature 0, fixed prompts).
- Every decision carries exact supporting quote(s) from the source PDF.
- Clear fixed steps, one after another, no free-running agent.
- Uncertainty and extraction gaps become "Needs a person to check" (never auto-approve).
- Runnable by a reviewer with one command and a README (OpenAI **or** Ollama).
- Testable against the 10 golden labels.

Non-goals (for this round):
- No real customer/company data; only the supplied sample files.
- No multi-language OCR; PDFs are text-based.
- No autonomous supplier negotiation or email sending.
- No persistent multi-tenant auth (single local user is fine).
- No live LangGraph interrupt UI required for MVP (batch "Needs person" is enough).

### 4.1 MVP vs nice-to-have (72-hour cut line)

**Must ship (MVP):**
- Fixed LangGraph nodes, LLM extraction-only, Python rule engine.
- Evidence substring checks, arithmetic checks, golden-label 10/10.
- JSONL audit under `runs/<timestamp>/`.
- Streamlit: batch run, results table, detail/evidence view.
- README + `.env.example` with OpenAI **and** Ollama paths.

**Ship only if time remains:**
- Live LangGraph `interrupt()` human-review form.
- SQLite (JSONL alone is enough for the demo).
- LangSmith tracing.
- Docker, OCR, concurrency (Phase 10).

## 5. Proposed stack (and why)

| Layer | Choice | Why this and not the alternative |
|---|---|---|
| Language | Python 3.11 | Best ecosystem for PDF, LLM, and workflow tooling; reviewers can run easily |
| Workflow engine | LangGraph (`StateGraph`) | Explicitly named in the brief; gives fixed nodes/edges, state, and human-interrupt support. Rejected n8n (harder to version/test in git) and LlamaIndex Workflows (less mature HITL) |
| Schemas | Pydantic v2 | Single source of truth for extraction output, state, and API; strict validation |
| LLM access | OpenAI-compatible client (`openai` SDK) behind a small adapter | Works with OpenAI **or** Ollama/vLLM via `LLM_BASE_URL`/`LLM_MODEL`. Demo default `gpt-4o-mini` at temperature 0; reviewers without a key can use Ollama. Rejected hard-coding one vendor |
| Structured output | JSON mode + Pydantic validation (with `instructor` optional) | Forces schema; any parse failure becomes "needs human", never a guess |
| PDF text | `pdfplumber` primary, `pypdf` fallback | `pdfplumber` preserves table layout better for quotation rows; fallback keeps it runnable if install fails |
| HTTP/UI | Streamlit | Fastest honest demo for a non-technical reviewer; shows table + evidence. Rejected a full React/Next app (too much surface for 72h) |
| Storage | JSONL audit log (SQLite optional) | Zero-setup, file-based, easy to inspect; SQLite only if time remains for a review queue |
| Packaging | `uv` + `pyproject.toml` | Reproducible installs; `uv run` one-liner for reviewers |
| Tests | `pytest` + golden-label fixtures | Directly measures the 25% "works on sample files" score |
| Lint/format | `ruff` | Fast, standard |
| Optional tracing | LangSmith (env-gated) | Debug prompts without coupling to it |

Key decision: **LLM is used only for extraction + evidence quoting. All decisions are made by deterministic Python rules.** This is the single most important design choice: it makes results reproducible, auditable, and defensible in the Loom video, and it directly satisfies "never guesses".

## 6. Architecture

See `ARCHITECTURE.md` for Mermaid workflow, component, decision-precedence,
verification-gate, provider-resolution, and golden-label diagrams.

### 6.1 High-level flow

```text
PDF -> ingest -> extract (LLM, schema) -> normalize/validate
     -> load PR row -> compare qty/price -> rule engine -> decide
     -> uncertainty gate -> (human review if needed) -> audit store -> UI
```

### 6.2 LangGraph nodes (fixed order, no branching except the review gate)

1. `ingest_document`
   - Read PDF, extract raw text per page, compute sha256, store `raw_text`.
   - Fail soft: if text is empty/too short, set `ingestion_ok=false` and route to human review.

2. `extract_quotation`
   - LLM call with a strict system prompt + JSON schema (`QuotationExtraction`).
   - Output fields + per-field `evidence` quote + `confidence` (0-1).
   - Temperature 0. No tools, no agent loop.

3. `verify_extraction`
   - **Primary gates (trust these):** required fields present; every `evidence`
     string is a substring (after whitespace normalization) of `raw_text`;
     arithmetic `qty * unit_price == line_amount` (and subtotal/VAT/total) within
     0.01 BDT.
   - **Secondary gate (do not rely on alone):** LLM self-reported confidence.
     Models are poor calibrators; treat `confidence < 0.80` as a soft signal that
     can tip an already-weak field to `needs_human`, never as proof of truth.
   - Set `extraction_status` = `ok` | `needs_human`, with a list of reasons.

4. `load_purchase_request`
   - Read `purchase-request.csv`, select the row whose `Item` equals extracted item code.
   - If no matching row, set `pr_match_ok=false` and route to human review.

5. `compare_to_pr`
   - `qty_diff_pct`, `price_diff_pct` (signed and absolute).
   - `price_over_max_pct`.

6. `check_rules`
   - Pure Python function `apply_rules(state) -> RuleResult` implementing section 7.
   - Returns `decision`, `reasons[]`, `evidence_refs[]`, `rule_hits[]`.

7. `decide_and_format`
   - If `extraction_status != ok` OR `pr_match_ok == false`: override decision to
     "Needs a person to check" with reason "Could not reliably extract/verify: ...".
   - Otherwise keep rule result.
   - Build final `DecisionRecord`.

8. `human_review_gate` (MVP = soft gate)
   - **MVP:** if `human_review_required`, write decision as
     "Needs a person to check" and add the record to the UI review list.
     Never auto-approve. No live interrupt required.
   - **Optional (time permitting):** LangGraph `interrupt()` so a reviewer can
     correct fields / override the decision in-session.

9. `persist_audit`
   - **MVP:** write `runs/<timestamp>/results.jsonl` with inputs hash, extraction,
     decision, evidence, model name, prompt version, timestamp.
   - **Optional:** also mirror rows into SQLite for a richer review queue.

### 6.3 State schema (Pydantic)

```python
class FieldExtraction(BaseModel):
    value: Any | None
    evidence: str | None
    confidence: float

class QuotationExtraction(BaseModel):
    supplier_name: FieldExtraction
    quotation_no: FieldExtraction
    quotation_date: FieldExtraction
    item_code: FieldExtraction          # A-E
    description: FieldExtraction
    quantity: FieldExtraction           # number
    unit: FieldExtraction
    unit_price: FieldExtraction         # number
    currency: FieldExtraction
    line_amount: FieldExtraction        # number
    subtotal: FieldExtraction
    vat_rate: FieldExtraction           # number, expect 15
    vat_amount: FieldExtraction
    total: FieldExtraction
    advance_payment_pct: FieldExtraction
    balance_payment_days: FieldExtraction  # int or range text
    payment_terms_text: FieldExtraction
    delivery_days: FieldExtraction       # int (convert weeks)
    late_penalty_clause_present: FieldExtraction  # bool
    late_penalty_pct_per_week: FieldExtraction   # number or null
    validity_days: FieldExtraction
    tin: FieldExtraction
    bin: FieldExtraction

class GraphState(BaseModel):
    doc_id: str
    raw_text: str
    text_hash: str
    ingestion_ok: bool
    extraction: QuotationExtraction | None
    extraction_status: Literal["ok", "needs_human"]
    extraction_issues: list[str]
    pr_row: dict | None
    pr_match_ok: bool
    qty_diff_pct: float | None
    price_diff_pct: float | None
    rule_result: RuleResult | None
    decision: Literal["Approve", "Reject", "Needs a person to check"] | None
    reasons: list[str]
    evidence: list[str]
    human_review_required: bool
    human_decision: str | None
```

### 6.4 Decision precedence (important)

1. Uncertain extraction / missing PR match -> **Needs a person to check** (never Reject,
   because we are not sure).
2. Any Reject rule -> **Reject**.
3. Any Needs rule -> **Needs a person to check**.
4. Otherwise -> **Approve**.

## 7. Rule engine (deterministic, pure Python)

```python
def apply_rules(s, pr):
    reasons, evidence, hits = [], [], []

    # Reject rules
    if price_over_max_pct(s) > 3.0:
        reject("Unit price is more than 3% above the maximum unit price in the PR",
               evidence=price_evidence)
    if advance_pct(s) > 20.0:
        reject("Advance payment is more than 20%")
    if not late_penalty_clause_present(s):
        reject("The contract has no late-delivery penalty clause")
    if tin_missing(s) or bin_missing(s):
        reject("The supplier's TIN or BIN is missing")
    # Only Reject when a delivery promise exists AND exceeds 45 days.
    # Missing / unparseable delivery is NOT a Reject (rule text does not say that).
    if delivery_days(s) is not None and delivery_days(s) > 45:
        reject("Delivery is promised later than 45 days after the purchase order")

    if any reject: return Reject

    # Needs rules
    if 0 < price_over_max_pct(s) <= 3.0:
        needs("Unit price is above the maximum, but by no more than 3%")
    if abs(qty_diff_pct(s)) > 5.0:
        needs("Quantity differs from the quantity requested by more than 5%")
    if payment_terms_unclear_or_outside_30_60(s):
        needs("Payment terms are unclear, or outside 30 to 60 days after delivery")
    if delivery_days(s) is None:
        needs("Delivery days could not be determined from the document")
    elif 31 <= delivery_days(s) <= 45:
        needs("Delivery is promised in 31 to 45 days")
    if not vat_shown_separately_at_15(s):
        needs("VAT is not shown separately at 15%")
    if not numbers_add_up(s):
        needs("The numbers do not add up (line total / subtotal / VAT / total)")
    if validity_days(s) is not None and validity_days(s) < 30:
        needs("The quotation is valid for less than 30 days")

    # Other notes (not listed under Reject; prefer Needs when below floor)
    if late_penalty_pct_per_week(s) is not None and late_penalty_pct_per_week(s) < 0.5:
        needs("Late-delivery penalty is below 0.5% of order value per week")

    if any needs: return Needs
    return Approve
```

Boundary convention: "more than 3%" means `> 3.0`, "less than 30 days" means `< 30`,
"31 to 45 days" is inclusive. Money compared with `abs(a-b) <= 0.01`.

Pack 10 note: Reject on delivery 60 days (>45). Do **not** invent a VAT-exclusive
unit price to compare against the PR max. VAT not shown separately is recorded as
an additional Needs reason / rule hit, but Reject already wins on precedence.

## 8. "Never guess" mechanisms

Ordered by reliability (use in this order when explaining the Loom):

1. Strict JSON schema; missing/invalid required field -> `extraction_status=needs_human`.
2. Evidence must be a substring of the source text (whitespace-normalized); if not,
   the field is unverified -> needs human.
3. Arithmetic cross-checks; mismatch is a first-class "Needs" reason, not a silent fix.
4. PR row must match by item code; if not, needs human.
5. LLM self-confidence is a **weak secondary signal only** (threshold 0.80). Never
   treat high confidence as proof if evidence/arithmetic fail.
6. Batch/MVP mode never auto-approves an uncertain record; it is written as
   "Needs a person to check".
7. All prompts versioned in `prompts/` and hashed into the audit log.
8. Temperature 0 + fixed seed where the provider supports it.

## 9. Storage and audit

**MVP:** `runs/<timestamp>/results.jsonl` for easy diffing and README reproducibility.
Every output includes: decision, reasons, evidence quotes, confidence, model, prompt
version, timestamp. This is what makes the Loom "why" credible.

**Optional SQLite** (only if building the richer review queue):
- `documents(doc_id, file_name, sha256, raw_text, created_at)`
- `extractions(doc_id, json, model, prompt_version, created_at)`
- `decisions(doc_id, decision, reasons_json, evidence_json, human_review_required, created_at)`
- `human_reviews(doc_id, reviewer, decision, notes, created_at)`

## 10. UI (Streamlit)

**MVP pages:**
- **Run batch**: select folder, run all 10, show progress.
- **Results table**: doc, supplier, item, qty diff, price diff, decision, reason.
- **Detail view**: raw PDF text, extracted fields with evidence highlighted, rule hits.

**Optional:**
- **Review queue**: form to approve/reject/annotate uncertain records (pairs with
  live HITL interrupt / SQLite).

The detail view is the demo's money shot: it shows the exact quote supporting each
decision, which is what a non-technical reviewer can follow.

## 11. Evaluation plan

Metrics reported in the one-page note:
- Decision accuracy on the 10 samples (target 10/10).
- Per-rule hit counts (how many Reject/Needs and why).
- Extraction field coverage (required fields present).
- Evidence coverage (% of reasons with a supporting quote).
- Uncertainty rate (how often the system said "I am not sure").
- Latency per document and total batch time.
- Cost per document (tokens).

Tests:
- `test_golden_labels.py`: assert decision + primary reason for all 10.
- `test_rule_engine.py`: boundary values for every rule.
- `test_extraction_schema.py`: schema validation + evidence substring check.
- `test_arithmetic.py`: money calculations.
- `test_pr_match.py`: item lookup.

## 12. Phase-by-phase implementation plan

### Phase 0 - Data inspection (done)
- Read brief, README, rules, PR CSV, extract all 10 PDFs.
- Produce golden labels (section 3).
- Acceptance: golden table agreed and checked.

### Phase 1 - Project scaffold
- Create `supplier-doc-check/` with `pyproject.toml`, `uv.lock`, `.env.example`,
  `README.md`, `src/`, `tests/`, `prompts/`, `data/`.
- Add ruff, pytest config.
- Acceptance: `uv sync` succeeds; `uv run pytest` runs (0 tests green).

### Phase 2 - Ingestion + extraction schema
- Implement PDF text extraction (`pdfplumber` -> `pypdf` fallback).
- Define `QuotationExtraction`, `FieldExtraction`, `GraphState` in Pydantic.
- Write prompt `prompts/extract_quotation.md` with JSON schema + evidence instructions.
- Acceptance: running on pack-01 yields non-empty text and a validated extraction.

### Phase 3 - LLM extraction node
- Implement adapter + `extract_quotation` node, temperature 0.
- Store raw extraction JSON.
- Acceptance: all 10 produce parseable JSON; required fields present or flagged.

### Phase 4 - Verification node
- Confidence threshold, evidence substring check, arithmetic checks.
- Acceptance: pack-09 line-total mismatch is detected; pack-10 VAT issue detected.

### Phase 5 - PR comparison + rule engine
- Implement `compare_to_pr` and `apply_rules`.
- Acceptance: golden labels match for all 10 when extraction is correct.

### Phase 6 - Decision + audit (MVP)
- Implement decision precedence and JSONL audit under `runs/<timestamp>/`.
- Soft human gate: uncertain -> "Needs a person to check", never auto-approve.
- Acceptance: uncertain records are never Approve; JSONL is reproducible.

### Phase 6b - HITL + SQLite (optional)
- LangGraph `interrupt()` + SQLite review queue, only if Phase 7-9 still fit.
- Acceptance: reviewer can override a Needs record without breaking golden tests.

### Phase 7 - Streamlit UI
- Batch run, results table, detail/evidence view (review form optional).
- Acceptance: a non-technical user can run all 10 and see evidence in <=3 clicks.

### Phase 8 - Tests + evaluation
- Golden-label tests, boundary tests, arithmetic tests.
- Produce `reports/evaluation.md` with metrics.
- Acceptance: `uv run pytest` green; accuracy 10/10.

### Phase 9 - Demo + docs + Loom prep
- README run instructions, `.env.example`, one-page note draft, Loom script outline.
- Acceptance: fresh clone runs with documented steps.

### Phase 10 - Hardening (only if time remains)
- OCR fallback for scanned PDFs, concurrency, Dockerfile, retry/backoff, LangSmith.
- Acceptance: no regression in golden tests.

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| LLM hallucinates a field | Evidence substring check + confidence threshold + HITL |
| PDF table extraction loses columns | `pdfplumber` table extraction + raw text fallback; verify numbers |
| VAT-inclusive vs exclusive price (pack 10) | Reject on delivery >45; do not invent ex-VAT price; also record VAT Needs hit |
| Missing delivery days | Needs person — do **not** Reject (Reject only if days > 45) |
| Delivery in weeks not days | Normalize in extraction prompt and verify with regex |
| Payment terms as a range ("30-90 days") | Treat range/clear ambiguity as "unclear" -> Needs |
| LLM overconfident wrong field | Evidence substring + arithmetic beat self-confidence |
| Free-running agent temptation | Code review gate: only `StateGraph` with fixed nodes allowed; no tool-calling agent |
| Reviewer has no OpenAI key | Document Ollama via `LLM_BASE_URL` + `LLM_MODEL` in README / `.env.example` |
| Scope creep in 72h | Cut line in section 4.1; optional HITL/SQLite/LangSmith only after MVP |
| Over-claiming accuracy | Honest note lists all known gaps (section 14) |

## 14. Known limitations to state honestly in the final note

- Text-based PDFs only; scanned/image PDFs are not handled in v1 (OCR is Phase 10).
- Bangla text is not supported (not needed for Task 1).
- Payment-term parsing is heuristic; complex multi-clause terms may need human review.
- VAT-inclusive quotes are not reverse-engineered into ex-VAT unit prices; pack 10
  Rejects on delivery, and VAT-not-separate is an extra rule hit.
- LLM self-confidence is weakly calibrated; evidence and arithmetic are the real gates.
- Small models via Ollama may reduce extraction quality; OpenAI default recommended
  for the scored demo, Ollama documented so reviewers can still run without a paid key.
- MVP does not require live in-graph human interrupt; uncertain docs are labelled
  "Needs a person to check" for offline review.
- The system does not send emails or update an ERP; it produces a decision + audit record.

## 15. Mapping to scoring (brief)

| Brief criterion | Weight | How this plan addresses it |
|---|---:|---|
| Loom presentation | 20% | UI detail view + evidence quotes + clear fixed steps |
| Works on sample files | 25% | Golden-label tests targeting 10/10 |
| Clear, sensible build, handles mistakes | 20% | Fixed LangGraph nodes, soft Needs gate, optional HITL |
| Hardest part (never guess) | 15% | Evidence + arithmetic primary; confidence secondary |
| Clean runnable code | 10% | uv, README, pytest, OpenAI or Ollama via `.env.example` |
| Honesty | 10% | Section 14 limitations + evaluation report |

## 16. Cursor agent instructions

See `agent.md` for repo conventions, commands, and the task checklist the Cursor agent
should follow when implementing this plan. Do not change the golden labels or rule
semantics without updating section 3 and section 7 together.