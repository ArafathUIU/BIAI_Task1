"""LLM extraction node (Phase 3).

The LLM is used ONLY for extraction + evidence quoting. It never decides
approve/reject/needs; that is the job of the deterministic rule engine.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from .config import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    OPENAI_API_KEY,
)
from .schemas import FieldExtraction, GraphState, QuotationExtraction

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "extract_quotation.md"


@lru_cache(maxsize=1)
def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def build_messages(raw_text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": load_prompt()},
        {"role": "user", "content": f"Document text:\n\n{raw_text}"},
    ]


def get_client_and_model() -> tuple[OpenAI, str]:
    """Resolve an OpenAI-compatible client + model from configuration."""
    if LLM_BASE_URL:
        api_key = LLM_API_KEY or OPENAI_API_KEY or "ollama"
        return OpenAI(base_url=LLM_BASE_URL, api_key=api_key), LLM_MODEL
    if GROQ_API_KEY:
        model = LLM_MODEL if LLM_MODEL and LLM_MODEL != "gpt-4o-mini" else GROQ_MODEL
        return OpenAI(base_url=GROQ_BASE_URL, api_key=GROQ_API_KEY), model
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "No LLM credentials configured. Set OPENAI_API_KEY, GROQ_API_KEY, "
            "or LLM_BASE_URL/LLM_API_KEY."
        )
    return OpenAI(api_key=OPENAI_API_KEY), LLM_MODEL


def call_llm(messages: list[dict[str, str]], *, client: OpenAI | None = None, model: str | None = None) -> str:
    """Call the chat completions endpoint. Tries JSON mode, falls back if unsupported."""
    if client is None or model is None:
        client, model = get_client_and_model()
    assert client is not None and model is not None

    base_kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": LLM_TEMPERATURE,
    }
    variants = [
        {"response_format": {"type": "json_object"}, "seed": 42},
        {"seed": 42},
        {},
    ]
    last_exc: Exception | None = None
    for extra in variants:
        try:
            response = client.chat.completions.create(**base_kwargs, **extra)
            content = response.choices[0].message.content
            if not content:
                raise RuntimeError("LLM returned an empty response.")
            return content
        except Exception as exc:  # noqa: BLE001 - provider capability varies
            last_exc = exc
    assert last_exc is not None
    raise last_exc


def _unwrap_payload(data: Any) -> Any:
    """Unwrap a single-key wrapper if the model nested the extraction."""
    if isinstance(data, dict) and "supplier_name" not in data and len(data) == 1:
        candidate = next(iter(data.values()))
        if isinstance(candidate, dict) and "supplier_name" in candidate:
            return candidate
    return data


def parse_extraction(payload: str | dict[str, Any]) -> tuple[QuotationExtraction | None, list[str]]:
    """Parse and validate LLM output into a QuotationExtraction."""
    issues: list[str] = []
    try:
        data = json.loads(payload) if isinstance(payload, str) else payload
    except (json.JSONDecodeError, TypeError) as exc:
        return None, [f"LLM output is not valid JSON: {exc}"]

    data = _unwrap_payload(data)
    try:
        extraction = QuotationExtraction.model_validate(data)
    except ValidationError as exc:
        # Keep the error readable but bounded.
        errors = exc.errors()
        summary = "; ".join(
            f"{'.'.join(str(p) for p in e.get('loc', ()))}: {e.get('msg')}" for e in errors[:8]
        )
        return None, [f"Schema validation failed: {summary}"]
    return extraction, issues


def _recover_item_code(extraction: QuotationExtraction, raw_text: str) -> QuotationExtraction:
    """Fill a missing item_code using a deterministic, evidence-backed parse."""
    if extraction.item_code.value is not None:
        return extraction
    match = re.search(r"(?m)^([A-E])\s+.+\d", raw_text)
    if match:
        line = match.group(0).strip()
        extraction.item_code = FieldExtraction(
            value=match.group(1),
            evidence=line,
            confidence=0.7,
        )
    return extraction


def extract_quotation(state: GraphState) -> GraphState:
    """LangGraph node: extract structured fields from the document text."""
    if not state.ingestion_ok or not state.raw_text.strip():
        state.extraction_status = "needs_human"
        state.extraction_issues.append("Ingestion failed; no text available for extraction.")
        return state

    messages = build_messages(state.raw_text)
    required = ("item_code", "quantity", "unit_price", "delivery_days")
    extraction: QuotationExtraction | None = None
    issues: list[str] = []
    last_exc: Exception | None = None

    for _ in range(3):
        try:
            content = call_llm(messages)
        except Exception as exc:  # noqa: BLE001 - any failure must become needs_human, never a guess
            last_exc = exc
            continue
        extraction, issues = parse_extraction(content)
        if extraction is not None and not any(
            getattr(extraction, field).value is None for field in required
        ):
            break

    if last_exc is not None and extraction is None:
        state.extraction_status = "needs_human"
        state.extraction_issues.append(f"LLM call failed: {last_exc}")
        return state
    if extraction is None:
        state.extraction_status = "needs_human"
        state.extraction_issues.extend(issues)
        return state

    # Deterministic recovery for a field the model occasionally omits.
    extraction = _recover_item_code(extraction, state.raw_text)

    state.extraction = extraction
    state.extraction_status = "ok"
    return state
