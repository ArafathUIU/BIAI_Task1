# Decisions.md - Why we chose this approach (Task 1)

This file records the **actual decisions** behind `PLAN.md` and `agent.md`, with the
logic for each. It is written to be read by a reviewer (human or Cursor agent)
before implementation. If a decision changes, update the relevant row here and in
`PLAN.md` in the same commit. See `ARCHITECTURE.md` for Mermaid diagrams of the
workflow, components, decision precedence, and verification gates.

Order: most important decisions first.

---

## D0. Choose Task 1 over Task 2

**Context:** The brief offers two tasks. We only have 72 hours and one deliverable.

**Decision:** Build Task 1 (supplier document checker).

**Logic:**
- Task 1 has a **verifiable ground truth**: 10 documents, a PR CSV, and an explicit
  rule list. We can prove 10/10 accuracy with tests. Task 2's "correctness" on 40
  mixed-language questions is fuzzier and harder to defend in a 5-minute Loom.
- Task 1's hardest part (never guess) maps directly to skills the role needs:
  schema validation, evidence grounding, deterministic rules, human-in-the-loop.
- Task 1 needs no GPU/Colab and no model fine-tuning, so the 72-hour risk is lower.
- Task 2 is still valuable but is a different risk profile (offline model quality);
  we keep it as a future project.

**Trade-off:** We give up the "bilingual offline assistant" story. We state this
honestly in the final note rather than attempting both.

---

## D1. Fixed workflow (LangGraph) instead of one free-running agent

**Context:** The brief explicitly says "build it as clear fixed steps... Do not
build one agent that runs freely on its own."

**Decision:** A `StateGraph` with named nodes and explicit edges. No tool-calling
agent loop.

**Logic:**
- The task is a checklist with a known order (extract → compare → rules → decide).
  A free agent adds non-determinism and makes the Loom harder to explain.
- Fixed nodes are independently testable (each node = one unit).
- Auditability: a reviewer can point to "step 4 applied rule 2" instead of
  "the agent decided."
- LangGraph is named in the brief, so it signals compliance to graders.

**Rejected:** n8n (harder to version/test in git, less code-reviewable), LlamaIndex
Workflows (less mature human-interrupt support at the time of planning).

---

## D2. LLM is extraction-only; decisions are deterministic Python

**Context:** The core risk is "never guess." If the LLM decides approve/reject, a
hallucination becomes a wrong business decision.

**Decision:** LLM outputs structured fields + evidence + confidence. A pure Python
`apply_rules()` function makes the final call.

**Logic:**
- Separation of concerns: language understanding (LLM strength) vs. rule application
  (code strength).
- Reproducibility: same input + same prompt version → same decision, every run.
- Testability: rule engine can be unit-tested without any LLM call.
- Explainability in the Loom: "the code applied rule 3, here is the quote."

**Trade-off:** We depend on extraction quality. We mitigate with evidence substring
checks, arithmetic checks, and human review (D8).

---

## D3. OpenAI-compatible adapter (OpenAI default, Ollama supported)

**Context:** Reviewers may not have an OpenAI key; the brief values runnable code.

**Decision:** Use the `openai` SDK behind a small adapter driven by
`LLM_BASE_URL`/`LLM_MODEL`. Default `gpt-4o-mini` at temperature 0; Ollama works
by setting the base URL.

**Logic:**
- One code path for both providers reduces maintenance.
- Temperature 0 + versioned prompts give determinism.
- Not hard-coding a vendor keeps the project runnable in more environments.
- Ollama support is documented as a fallback, not the scored default, because
  small models may reduce extraction quality on 10 documents.

**Trade-off:** Two providers means two failure modes; we keep the adapter thin and
test the schema, not the provider.

---

## D4. Pydantic v2 schemas as the single source of truth

**Context:** Extraction output, graph state, and audit records must agree.

**Decision:** `FieldExtraction` and `QuotationExtraction` Pydantic models define
the contract; the LLM is asked for JSON matching them; validation failures become
"needs human."

**Logic:**
- Strict validation converts "model said something weird" into a controlled
  `needs_human` state instead of a crash or a guess.
- One schema drives the prompt, the parser, the UI, and the audit log.
- Pydantic v2 is fast and standard in the Python LLM ecosystem.

---

## D5. PDF text: pdfplumber primary, pypdf fallback

**Context:** Quotations are tables; layout matters for reading rows correctly.

**Decision:** `pdfplumber` first (better table extraction), `pypdf` fallback.

**Logic:**
- pdfplumber preserves column structure better for `qty * unit_price` checks.
- A fallback keeps the project runnable if an install fails on a reviewer's
  machine.
- Both are pure-Python, no system dependencies.

**Trade-off:** No OCR in v1. Scanned PDFs are out of scope and stated as a
limitation (honesty score).

---

## D6. Evidence must be a substring of the source text

**Context:** LLMs can quote plausible but invented text.

**Decision:** Every `evidence` string is checked (whitespace-normalized) against
`raw_text`. If it is not a substring, the field is unverified → needs human.

**Logic:**
- This is the single strongest anti-hallucination control available without a
  second model.
- It directly supports "Always quote the exact text from the document" in
  `company-rules.md`.
- It makes the UI detail view trustworthy: the highlighted quote really exists.

**Implementation note:** normalize whitespace in *both* strings before the check,
because PDF extraction inserts line breaks.

---

## D7. Arithmetic cross-checks are first-class "Needs" reasons

**Context:** Pack 09 has a line total that does not add up (6.40 × 50,000 = 320,000
but the document says 322,000).

**Decision:** Compute `qty * unit_price`, subtotal, 15% VAT, and total; mismatches
become explicit "The numbers do not add up" reasons.

**Logic:**
- Rule #6 in `company-rules.md` lists this as a "Needs person" trigger.
- Arithmetic is deterministic and cheap, so there is no reason to trust the model.
- Catching it automatically demonstrates the "handles mistakes" scoring criterion.

---

## D8. Conservative human review (never auto-approve uncertain data)

**Context:** The brief says "When it is not sure, stop and ask a person. Do not guess."

**Decision:** Any failed extraction/verification/PR-match sets `human_review_required`
and the decision becomes "Needs a person to check." Batch/MVP mode never
auto-approves.

**Logic:**
- A false Approve on a bad supplier document is worse than a false "Needs person."
- "Needs a person to check" is a valid final answer per the brief, so we are not
  failing by using it.
- This is the "hardest part" (15% weight) and the main thing the Loom must show.

**MVP scope:** soft gate (label + review list), not a live LangGraph `interrupt()`.
Live HITL is optional (Phase 6b) to protect the 72-hour cut line.

---

## D9. Confidence is a weak secondary signal only

**Context:** LLM self-reported confidence is poorly calibrated.

**Decision:** Do not gate on confidence alone. Use `confidence < 0.80` only to tip
an already-weak field (failed evidence or missing required field) into
`needs_human`.

**Logic:**
- Evidence substring + arithmetic are objective; confidence is subjective.
- Treating confidence as proof would reintroduce guessing.
- We still record confidence in the audit log for transparency and Loom discussion.

---

## D10. JSONL audit (MVP) instead of SQLite-first

**Context:** We need an audit trail for the Loom and README reproducibility, but
SQLite + a review UI is extra surface.

**Decision:** Write `runs/<timestamp>/results.jsonl` with inputs hash, extraction,
decision, evidence, model, prompt version, timestamp. SQLite is optional (Phase 6b).

**Logic:**
- JSONL is human-readable, diffable, and zero-setup.
- It satisfies the one-page note's "how you tested it" requirement.
- SQLite only earns its cost if we build the live review queue.

---

## D11. Streamlit for the demo UI

**Context:** A non-technical reviewer must follow the 5-minute Loom.

**Decision:** Streamlit with batch run, results table, and detail/evidence view.

**Logic:**
- Fastest path to a credible demo in 72 hours.
- Shows the "money shot": exact source quote supporting each decision.
- No frontend build tooling; reviewers run with `uv run streamlit run ...`.

**Rejected:** React/Next (too much surface area for the time budget).

---

## D12. Conservative handling of ambiguous delivery and VAT-inclusive pricing

**Context:** Pack 10 quotes a VAT-inclusive unit price and 60-day delivery.

**Decisions:**
1. Missing/unparseable delivery days → "Needs person," not Reject (Reject only when
   a numeric promise exists and is `> 45`).
2. VAT-inclusive price → Reject on delivery 60 days; do **not** invent an ex-VAT
   unit price for comparison; record "VAT not shown separately" as an extra hit.
3. If VAT is not shown separately, do not emit a price-over-max reason (price
   comparison is not meaningful); only non-price rules decide.

**Logic:**
- Rule 5 Reject is specifically "later than 45 days," not "missing."
- Inventing an ex-VAT price would be guessing, which violates the brief.
- Avoiding a price reason in the VAT-inclusive case prevents a misleading
  "price OK" signal.

**Note (v1 scope):** Extreme VAT-inclusive overpricing (e.g. unit price far above
max even before tax) is left as **Needs** via the VAT rule, not reverse-engineered
into a price **Reject**. Acceptable under "never guess." Revisit only with explicit
tax math **and** human confirmation — never silent `/1.15` Rejects.

---

## D13. Golden labels are the acceptance target and must not be edited to pass

**Context:** Tests must measure real accuracy, not be retrofitted.

**Decision:** `tests/fixtures/expected.json` holds the 10 decisions and primary
reasons. If a label seems wrong, update `PLAN.md` §3 and §7 together with
justification.

**Logic:**
- Prevents "test hacking" from inflating the 25% accuracy score.
- Forces rule changes and label changes to be reviewed together.
- Keeps the Cursor agent honest (see `agent.md` rule 6).

---

## D14. Ollama documented as fallback, not scored default

**Context:** Task 1 does not require offline, but runnable code matters (10%).
(Product stance for the same adapter described in D3.)

**Decision:** OpenAI default for the scored demo; Ollama documented via env vars.

**Logic:**
- Small models may reduce extraction quality on these 10 documents.
- We do not want extraction uncertainty to mask a correct rule engine.
- Reviewers without a key can still run the project, which protects the
  "clean runnable code" score.

---

## D15. Late-delivery penalty floor (< 0.5%/week) → Needs, not Reject

**Context:** `company-rules.md` Rejects when there is **no** late-delivery penalty
clause. Under "Other notes" it also says the penalty must be at least **0.5% of
order value per week**. That floor is not listed under Reject or Needs.

**Decision:**
1. **No penalty clause at all** → **Reject** (explicit Reject rule #3).
2. Clause present but `late_penalty_pct_per_week < 0.5` → **Needs a person to check**
   (not Reject).
3. Clause present and `>= 0.5` → no hit from this rule.

**Logic:**
- Reject text only covers absence of a clause, not an undersized rate.
- Mapping the "Other notes" floor to Needs follows "if you are not sure… Needs"
  and matches `PLAN.md` §7 / `agent.md` preference for Needs over inventing a
  Reject.
- Implementers must not silently promote `< 0.5%` to Reject.

---

## D16. Field status FOUND / NOT_FOUND / UNCERTAIN (narrow scope)

**Context:** LLM often set `value` with empty evidence and `confidence=0.00`
(the Pydantic default). Callers could not tell “absent after inspection” from
“model guessed” or “could not read the contract.”

**Decision:** Add optional `status` on `FieldExtraction`:
- **FOUND** — value supported by source evidence
- **NOT_FOUND** — relevant content inspected; information is absent
- **UNCERTAIN** — incomplete / ambiguous / unverified

Apply this rigorously to `late_penalty_clause_present` (and lightly to cleared
optional fields). Do **not** force status/page-number on every commercial field
in this round — the sample PDFs are one page and rules do not need address/contact.

**Logic:** Matches “never guess” without a full OCR/page-platform rewrite.
Confidence defaults to `null` until evidence or a deterministic scan sets it;
`0.00` is no longer treated as a real score.

---

## D17. Deterministic late-penalty clause scan (Python, not LLM)

**Context:** Pack 06 has no late-delivery penalty clause. The LLM sometimes
emitted `false` with no quote and confidence 0. An empty extract is not proof of
absence.

**Decision:** After ingest, `scan_late_penalty_clause(raw_text)` in `clauses.py`
overwrites the LLM field:
1. T&C (or substantial body) inspectable + penalty wording → **FOUND / true** +
   exact quote
2. T&C inspectable + no penalty wording → **NOT_FOUND / false** + inspected
   snippet as evidence; confidence mid (e.g. 0.75), never 1.0
3. Not enough inspectable contract text → **UNCERTAIN / null**

Rules:
- `absent` (NOT_FOUND/false) → **Reject**
- `uncertain` → **Needs a person**
- `present` → no Reject from this rule

**Logic:** Absence is only asserted after inspection. No pack-name hardcoding.
Preserves pack 06 Reject without inventing evidence.

---

## D18. Confirmed Reject beats soft extraction uncertainty

**Context:** `decide()` previously short-circuited to Needs whenever
`extraction_status != ok`, hiding confirmed Rejects (e.g. 40% advance) behind
optional-field evidence noise.

**Decision:** Precedence:
1. Ingest / no extraction / no PR match → Needs
2. Run rules on available verified facts; if decision is **Reject** → **Reject**
3. Else if extraction still uncertain → Needs
4. Else use rule result (Needs or Approve)

**Logic:** Spec §8 / company rules: a confirmed hard violation must not be
hidden by another uncertainty. We do **not** weaken evidence rules to inflate
Approve rates.

---

## D19. Defer OCR / PyMuPDF / page numbers for Task 1 sample set

**Context:** A broader “document intelligence” brief asked for PyMuPDF, Tesseract
OCR, and page numbers on every field.

**Decision:** Keep `pdfplumber` + `pypdf` for this round. All 10 sample packs are
text-based single-page PDFs. OCR and page metadata stay Phase 10 / future work.

**Logic:** Protects the 72h cut line and golden-label focus. Empty extract still
means UNCERTAIN, never NOT_FOUND.

---

## D20. Late-penalty scanner must accept equivalent wording (Pack 02 fix)

**Context:** Pack 02 says *“For late delivery the supplier shall pay 0.75% … per
week of delay”* (no word “penalty”). D17 patterns used `[^\n.]` windows that
stopped at the decimal in `0.75%`, and required the literal “penalty”, causing a
false NOT_FOUND → false Reject.

**Decision:**
1. Match equivalent contractual consequences (shall/will pay, deduction,
   liquidated damages, order-value % per week of delay) — not only the word
   “penalty”.
2. Use decimal-safe windows (`[^\n]` / explicit `\d+(?:\.\d+)?\s*%`) so rates
   like 0.75%, 1.25%, 2.0% parse.
3. Require a real late-delivery consequence; do not FOUND on VAT%, advance%, or
   late-*payment* interest alone.
4. FOUND evidence = exact clause line; NOT_FOUND evidence = inspected section
   marker (T&C header), not an unrelated Payment snippet.
5. When FOUND, derive `late_penalty_pct_per_week` from that evidence.

**Logic:** Keeps D17’s inspect-before-absent rule and Pack 06 Reject, without
weakening company thresholds or hardcoding pack names.

---

## D21. Percentage evidence–value reconciliation (Pack 05 fix)

**Context:** Pack 05 LLM returned `advance_payment_pct=0.4` with evidence
`40% advance…`. Substring evidence checks passed, but `0.4 > 20` is false, so
rules Approved. The model used a fraction instead of percent points. D20 already
normalizes `late_penalty_pct_per_week`; advance/VAT had no equivalent check.

**Decision:**
1. After substring evidence validation, reconcile `advance_payment_pct` and
   `vat_rate` against `N%` tokens in their evidence (percent points throughout).
2. Direct match (`40` vs `40%`, `0.4` vs `0.4%`) → FOUND.
3. Unambiguous fraction (`0.4` vs `40%`, with evidence rate ≥ 1) → normalize to
   percent points, FOUND, audit `Note: Normalized…`.
4. Mismatch / no usable `%` / ambiguous multiple `%` without reliable context →
   UNCERTAIN; clear the value; do not silently trust it.
5. Do **not** overwrite D20-owned `late_penalty_*` fields.
6. No pack-name hardcoding; thresholds and decide precedence unchanged.

**Logic:** Keeps company rule `advance > 20` meaningful when the LLM mis-scales
percents. Prefer Needs/UNCERTAIN over a false Approve from inconsistent numbers.

---

## Summary table

| # | Decision | Core reason |
|---|---|---|
| D0 | Task 1 | Verifiable ground truth in 72h |
| D1 | Fixed LangGraph workflow | Brief requires it; testable/auditable |
| D2 | LLM extraction-only | Never guess; reproducible |
| D3 | OpenAI-compatible adapter | Runnable anywhere; no vendor lock |
| D4 | Pydantic schemas | One contract; failures → needs human |
| D5 | pdfplumber + pypdf fallback | Table fidelity + portability |
| D6 | Evidence substring check | Strongest anti-hallucination control |
| D7 | Arithmetic as Needs reasons | Deterministic mistake detection |
| D8 | Conservative human review | False Approve is worse than Needs |
| D9 | Confidence secondary only | LLMs are poor calibrators |
| D10 | JSONL audit MVP | Zero-setup, diffable |
| D11 | Streamlit UI | Fastest credible demo |
| D12 | Ambiguous delivery/VAT handling | Avoid guessing; no silent ex-VAT Reject |
| D13 | Golden labels locked | No test hacking |
| D14 | Ollama as fallback | Runnable without paid key (see also D3) |
| D15 | Penalty below 0.5%/week → Needs | Other-notes floor is not a Reject rule |
| D16 | FOUND/NOT_FOUND/UNCERTAIN status | Absence ≠ failure ≠ guess |
| D17 | Deterministic late-penalty scan | Pack 06 Reject without LLM invention |
| D18 | Reject beats soft uncertainty | Hard violations stay visible |
| D19 | Defer OCR/page platform | Sample PDFs are text; keep scope tight |
| D20 | Equivalent late-pay wording + decimal-safe % | Fix Pack 02 false Reject |
| D21 | Percent evidence–value reconcile | Fix Pack 05 false Approve (0.4 vs 40%) |
| D22 | Control Center UI over existing pipeline | Live single/multi verify + separate Evaluation |

---

## D22. Supplier Verification Control Center (UI)

**Context:** Assignment demo needed real upload UX (1..N PDFs) without forcing the
10-pack ritual, while keeping Evaluation independent.

**Decision:** Streamlit Control Center wraps the existing LangGraph pipeline.
Live docs persist under `workspace/live/` (full `GraphState` JSON + PDF).
Evaluation runs the 10 samples against `expected.json` and never mutates golden
labels. Processing failures are stored as `failed` with no supplier decision.

## Reversal triggers

Revisit a decision only if:
- A golden label changes (D13 process).
- The 72-hour cut line is missed (then cut optional phases first, not MVP).
- A reviewer explicitly requests live HITL/SQLite (then do Phase 6b after MVP).
- Extraction accuracy on the 10 drops below 10/10 (then improve prompt/schema, not rules).