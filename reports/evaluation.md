# Evaluation Report — Task 1 Supplier Document Checker

## Summary

| Metric | Result |
|---|---|
| Packs evaluated | 10 |
| Target accuracy | 10/10 |
| Decision accuracy (golden labels) | 10/10 (when extraction is correct) |
| Tests passing | 59 |
| Ruff lint | Clean |

## Golden-label decisions

| Pack | Supplier | Item | Decision | Primary reason |
|---|---|---|---|---|
| 01 | Padma Textile Mills Ltd | A | Approve | All rules pass |
| 02 | Jamuna Trims and Accessories | B | Approve | All rules pass |
| 03 | Karnaphuli Yarn Traders | C | Reject | Unit price 9.05% above max (>3%) |
| 04 | Surma Packaging Industries | D | Needs a person to check | Unit price 2.31% above max (≤3%) |
| 05 | Meghna Carton Works | E | Reject | Advance payment 40% (>20%) |
| 06 | Teesta Fabrics Ltd | A | Reject | No late-delivery penalty clause |
| 07 | Rupsha Zipper Factory | B | Needs a person to check | Quantity 17.5% below requested (>5%) |
| 08 | Bhairab Thread and Co | C | Reject | TIN/BIN missing |
| 09 | Dhaleshwari Poly Pack | D | Needs a person to check | Payment terms unclear (30-90 days) + line total mismatch |
| 10 | Kushiyara Box Industries | E | Reject | Delivery 60 days (>45); VAT not shown separately |

Tally: **2 Approve, 5 Reject, 3 Needs a person to check.**

## Verification coverage

- **Evidence substring checks:** Every required field's evidence quote must be an exact substring of the source PDF text.
- **Arithmetic cross-checks:** `qty × unit_price = line_amount`, subtotal, VAT, and total are verified; mismatches are recorded as "Needs" reasons.
- **Percent reconciliation (D21):** `advance_payment_pct` and `vat_rate` are reconciled against `N%` tokens in their evidence; fractions (e.g. `0.4` for `40%`) are normalized to percent points.
- **Late-penalty scanner (D17/D20):** Deterministic scan overwrites bare LLM guesses; absence is only recorded after inspecting the T&C section.

## Decision precedence (D18)

1. Ingestion failure / no extraction / no PR match → **Needs a person to check**
2. Confirmed Reject rule → **Reject** (wins over soft extraction uncertainty)
3. Critical extraction uncertainty → **Needs a person to check**
4. Otherwise → rule result (Needs or Approve)

## How to run evaluation

```bash
# Unit tests (no LLM required)
uv run python -m pytest

# Golden-label lock tests (no LLM required)
uv run python -m pytest tests/test_golden_labels.py tests/test_rules.py tests/test_decide.py

# Live end-to-end evaluation (requires LLM provider)
uv run streamlit run src/supplier_check/ui.py
# Then open the Evaluation page and run "Run live evaluation (10 packs)"
```

Or via CLI:

```bash
uv run python -m supplier_check.graph --input data/ --out runs/
```

## Honesty notes

- Pack 05 was initially a false approve because the LLM returned `advance_payment_pct=0.4` (fraction) instead of `40` (percent points). Fixed via D21 percent reconciliation in `verify.py`.
- Pack 02 was initially a false reject because the LLM missed the late-penalty clause worded as "shall pay 0.75%". Fixed via D20 deterministic clause scanner in `clauses.py`.
- VAT-inclusive quotes (Pack 10) are not reverse-engineered into ex-VAT unit prices; they reject on delivery >45 days with VAT-not-separate as an additional hit.
- Small models via Ollama may reduce extraction quality; OpenAI/Groq recommended for the scored demo.
