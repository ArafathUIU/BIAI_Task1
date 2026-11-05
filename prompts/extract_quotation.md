# Extract quotation

You are extracting structured commercial data from a supplier quotation and its terms
and conditions. Output **only valid JSON** matching the schema below. Do not include
markdown, commentary, or any text outside the JSON.

## Rules

1. Use only information present in the document. Never invent or guess a value.
2. If a field is missing or unclear, set `value` to `null`, `evidence` to `null`,
   and `confidence` to `0.0`.
3. `evidence` must be an **exact substring** of the source document text. Do not
   paraphrase. If you cannot find an exact supporting quote, set the field to null.
4. `confidence` is a 0.0-1.0 estimate of how clearly the value is stated. It is a
   weak signal only; evidence and arithmetic are checked separately.
5. Numbers: use plain JSON numbers (no thousands separators, no currency symbols).
6. `item_code` must be one of A, B, C, D, E as printed in the quotation. It is the
   single letter in the "Item" column of the quotation table (often on its own line).
   Do not confuse it with the description.
7. `delivery_days`: integer number of days. Convert "N weeks" to N*7. If the
   document says "4 weeks", output 28.
8. `late_penalty_clause_present`: true only if a late-delivery penalty clause exists
   and you can quote it. If you cannot quote it, set value/evidence to null.
   Do not invent false. A deterministic scanner will re-check this field.
9. `late_penalty_pct_per_week`: numeric percent per week (e.g. 0.5), or null if
   no clause / not stated.
10. `tin` / `bin`: the supplier's TIN / BIN strings, or null if missing.
11. `balance_payment_days`: integer days if a single number is given; if a range
    (e.g. "30 to 90 days") is given, output the original phrase as a string.
12. `vat_rate`: numeric percent (expect 15). If VAT is included in the unit price
    and not shown separately, set `vat_rate` to null and `vat_amount` to null.
13. `advance_payment_pct`: numeric percent. If the document says no advance is
    required (e.g. "No advance payment required"), set `value` to `0` with that
    sentence as evidence — do not leave it null.

## Schema

```json
{
  "supplier_name": {"value": "string|null", "evidence": "string|null", "confidence": 0.0},
  "quotation_no": {"value": "string|null", "evidence": "string|null", "confidence": 0.0},
  "quotation_date": {"value": "string|null", "evidence": "string|null", "confidence": 0.0},
  "item_code": {"value": "string|null", "evidence": "string|null", "confidence": 0.0},
  "description": {"value": "string|null", "evidence": "string|null", "confidence": 0.0},
  "quantity": {"value": "number|null", "evidence": "string|null", "confidence": 0.0},
  "unit": {"value": "string|null", "evidence": "string|null", "confidence": 0.0},
  "unit_price": {"value": "number|null", "evidence": "string|null", "confidence": 0.0},
  "currency": {"value": "string|null", "evidence": "string|null", "confidence": 0.0},
  "line_amount": {"value": "number|null", "evidence": "string|null", "confidence": 0.0},
  "subtotal": {"value": "number|null", "evidence": "string|null", "confidence": 0.0},
  "vat_rate": {"value": "number|null", "evidence": "string|null", "confidence": 0.0},
  "vat_amount": {"value": "number|null", "evidence": "string|null", "confidence": 0.0},
  "total": {"value": "number|null", "evidence": "string|null", "confidence": 0.0},
  "advance_payment_pct": {"value": "number|null", "evidence": "string|null", "confidence": 0.0},
  "balance_payment_days": {"value": "number|string|null", "evidence": "string|null", "confidence": 0.0},
  "payment_terms_text": {"value": "string|null", "evidence": "string|null", "confidence": 0.0},
  "delivery_days": {"value": "number|null", "evidence": "string|null", "confidence": 0.0},
  "late_penalty_clause_present": {"value": "boolean|null", "evidence": "string|null", "confidence": 0.0},
  "late_penalty_pct_per_week": {"value": "number|null", "evidence": "string|null", "confidence": 0.0},
  "validity_days": {"value": "number|null", "evidence": "string|null", "confidence": 0.0},
  "tin": {"value": "string|null", "evidence": "string|null", "confidence": 0.0},
  "bin": {"value": "string|null", "evidence": "string|null", "confidence": 0.0}
}
```

## Input

The document text will be provided after this prompt. Return the JSON object only.
