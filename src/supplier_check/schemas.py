"""Pydantic schemas for extraction, graph state, and decisions."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FieldExtraction(BaseModel):
    """One extracted field with its supporting evidence and confidence."""

    model_config = ConfigDict(extra="forbid")

    value: Any = None
    evidence: str | None = None
    confidence: float = 0.0

    @field_validator("confidence")
    @classmethod
    def _clamp_confidence(cls, v: float) -> float:
        try:
            v = float(v)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, v))


class QuotationExtraction(BaseModel):
    """Structured extraction of a supplier quotation + terms and conditions."""

    model_config = ConfigDict(extra="forbid")

    supplier_name: FieldExtraction
    quotation_no: FieldExtraction
    quotation_date: FieldExtraction
    item_code: FieldExtraction
    description: FieldExtraction
    quantity: FieldExtraction
    unit: FieldExtraction
    unit_price: FieldExtraction
    currency: FieldExtraction
    line_amount: FieldExtraction
    subtotal: FieldExtraction
    vat_rate: FieldExtraction
    vat_amount: FieldExtraction
    total: FieldExtraction
    advance_payment_pct: FieldExtraction
    balance_payment_days: FieldExtraction
    payment_terms_text: FieldExtraction
    delivery_days: FieldExtraction
    late_penalty_clause_present: FieldExtraction
    late_penalty_pct_per_week: FieldExtraction
    validity_days: FieldExtraction
    tin: FieldExtraction
    bin: FieldExtraction


class RuleResult(BaseModel):
    """Output of the deterministic rule engine."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal["Approve", "Reject", "Needs a person to check"] | None = None
    reasons: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    rule_hits: list[str] = Field(default_factory=list)


class GraphState(BaseModel):
    """State passed between LangGraph nodes."""

    model_config = ConfigDict(extra="forbid")

    doc_id: str
    file_name: str | None = None
    file_path: str | None = None
    raw_text: str = ""
    text_hash: str = ""
    ingestion_ok: bool = False
    ingestion_issues: list[str] = Field(default_factory=list)

    extraction: QuotationExtraction | None = None
    extraction_status: Literal["ok", "needs_human"] = "needs_human"
    extraction_issues: list[str] = Field(default_factory=list)

    pr_row: dict[str, Any] | None = None
    pr_match_ok: bool = False
    qty_diff_pct: float | None = None
    price_diff_pct: float | None = None
    price_over_max_pct: float | None = None

    rule_result: RuleResult | None = None
    decision: Literal["Approve", "Reject", "Needs a person to check"] | None = None
    reasons: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    human_review_required: bool = False
    human_decision: str | None = None
    # Resolved provider model id used for extraction (OpenAI / Groq / Ollama).
    llm_model: str | None = None

