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
