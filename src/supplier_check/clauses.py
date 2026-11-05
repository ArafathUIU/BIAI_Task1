"""Deterministic clause scanners (no LLM).

Empty extraction is never treated as proof that a clause is absent. Absence is
only recorded as NOT_FOUND after the relevant document section was inspected.
"""

from __future__ import annotations

import re

from .schemas import FieldExtraction

_TERMS_HEADER = re.compile(r"(?is)terms\s+and\s+conditions")

# Decimal-safe percent token (0.75%, 1.25%, 2.0%, etc.). Never use [^\n.] windows
# that stop at the decimal point inside the rate.
_PCT = r"(\d+(?:\.\d+)?)\s*%"

# Contractual consequence for late / delayed delivery (not mere mention of delay).
_QUALIFYING_PATTERNS = (
    # "Late delivery penalty: 1% ..." / "penalty for late delivery"
    re.compile(
        r"(?is)(?:late\s+delivery\s+penalty|penalty\s+for\s+late\s+delivery|"
        r"late[\s-]+delivery[\s-]+penalty)"
    ),
    # "Delay in delivery will attract a penalty of 0.5% ..."
    re.compile(
        r"(?is)delay(?:\s+in\s+delivery)?[^\n]{0,80}?penalty[^\n]{0,80}?" + _PCT
    ),
    # "penalty of 0.5% ... per week" / "0.5% penalty per week"
    re.compile(
        r"(?is)penalty[^\n]{0,80}?" + _PCT + r"[^\n]{0,80}?"
        r"(?:per\s+week|each\s+(?:full\s+)?week|weekly)"
    ),
    re.compile(
        r"(?is)" + _PCT + r"[^\n]{0,40}?penalty[^\n]{0,40}?"
        r"(?:per\s+week|each\s+(?:full\s+)?week|weekly)"
    ),
    # "supplier shall pay 0.75% ... per week of delay" / late delivery ... shall pay
    re.compile(
        r"(?is)(?:late\s+delivery|delayed\s+delivery)[^\n]{0,100}?"
        r"(?:shall\s+pay|will\s+pay|pays?|deduct(?:s|ed|ion)?|charge[sd]?)[^\n]{0,80}?"
        + _PCT
    ),
    re.compile(
        r"(?is)(?:shall\s+pay|will\s+pay|pays?)[^\n]{0,80}?"
        + _PCT
        + r"[^\n]{0,80}?(?:per\s+week|each\s+(?:full\s+)?week)[^\n]{0,40}?delay"
    ),
    # Deduction / liquidated damages for delayed / late delivery
    re.compile(
        r"(?is)(?:deduction|deduct(?:ed|ion)?|liquidated\s+damages)[^\n]{0,60}?"
        r"(?:for\s+)?(?:late\s+|delayed\s+)?delivery"
    ),
    re.compile(r"(?is)liquidated\s+damages[^\n]{0,40}?delay"),
    # "% of (the) order value per week / each full week of delay"
    re.compile(
        r"(?is)"
        + _PCT
        + r"\s+of\s+(?:the\s+)?order\s+value[^\n]{0,40}?"
        r"(?:per\s+week|for\s+each\s+(?:full\s+)?week|each\s+(?:full\s+)?week)"
        r"[^\n]{0,20}?delay"
    ),
)

# Weekly rate extraction from a FOUND evidence quote (decimal-safe).
_RATE_PATTERNS = (
    re.compile(
        r"(?is)"
        + _PCT
        + r"\s*(?:of\s+(?:the\s+)?order\s+value\s*)?"
        r"(?:per\s+week|for\s+each\s+(?:full\s+)?week|each\s+(?:full\s+)?week|weekly)"
    ),
    re.compile(
        r"(?is)(?:per\s+week|each\s+(?:full\s+)?week|weekly)[^\n]{0,40}?" + _PCT
    ),
    re.compile(r"(?is)penalty[^\n]{0,40}?" + _PCT),
    re.compile(r"(?is)(?:shall\s+pay|will\s+pay|pays?|deduct)[^\n]{0,40}?" + _PCT),
)


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def _terms_section(raw_text: str) -> tuple[str, bool]:
    """Return (section_text, inspected_ok)."""
    text = raw_text or ""
    match = _TERMS_HEADER.search(text)
    if match:
        section = text[match.start() :]
        inspected = len(normalize_text(section)) >= 80
        return section, inspected
    # No explicit header: only treat as inspectable if the whole doc is substantial.
    section = text
    inspected = len(normalize_text(section)) >= 120
    return section, inspected


def _iter_clause_units(section: str) -> list[tuple[int, int, str]]:
    """Yield (start, end, text) for non-empty lines inside the inspected section."""
    units: list[tuple[int, int, str]] = []
    offset = 0
    for line in section.splitlines(keepends=True):
        stripped = line.strip()
        if stripped:
            local = line.find(stripped)
            start = offset + local
            end = start + len(stripped)
            units.append((start, end, stripped))
        offset += len(line)
    return units


def _exact_evidence(snippet: str, raw_text: str) -> str | None:
    """Return snippet only when it is an exact (whitespace-normalized) source quote."""
    if not snippet:
        return None
    if snippet in raw_text:
        return snippet
    if normalize_text(snippet) in normalize_text(raw_text):
        # Prefer the original snippet if normalized match holds (PDF newlines).
        return snippet
    return None


def extract_weekly_penalty_pct(evidence: str) -> float | None:
    """Parse a weekly late-delivery percentage from a FOUND evidence quote."""
    if not evidence:
        return None
    for pattern in _RATE_PATTERNS:
        hit = pattern.search(evidence)
        if not hit:
            continue
        for group in hit.groups():
            if group is None:
                continue
            try:
                return float(group)
            except ValueError:
                continue
    return None


def _unit_qualifies(unit_text: str) -> re.Match[str] | None:
    """Return the first qualifying match inside a clause unit, else None."""
    for pattern in _QUALIFYING_PATTERNS:
        hit = pattern.search(unit_text)
        if hit:
            return hit
    return None


def _inspected_section_marker(section: str, raw_text: str) -> str | None:
    """Evidence for NOT_FOUND: which section was inspected (not an unrelated snippet)."""
    header = _TERMS_HEADER.search(section)
    if header:
        marker = section[header.start() : header.end()]
        return _exact_evidence(marker, raw_text)
    # No header - record that the full inspectable body was checked.
    first = section.strip().splitlines()[0].strip() if section.strip() else None
    if first:
        return _exact_evidence(first, raw_text)
    return None


def scan_late_penalty_clause(raw_text: str) -> FieldExtraction:
    """Classify late-delivery penalty as FOUND / NOT_FOUND / UNCERTAIN.

    - FOUND (true): qualifying consequence located; evidence is an exact source quote.
    - NOT_FOUND (false): T&C (or full doc) inspected; no qualifying clause found.
    - UNCERTAIN (null): not enough inspectable contract text.
    """
    section, inspected = _terms_section(raw_text)
    if not inspected:
        return FieldExtraction(
            value=None,
            evidence=None,
            confidence=None,
            status="UNCERTAIN",
        )

    for _start, _end, unit_text in _iter_clause_units(section):
        hit = _unit_qualifies(unit_text)
        if not hit:
            continue
        # Prefer the full clause line as evidence when it is an exact source quote.
        evidence = _exact_evidence(unit_text, raw_text)
        if evidence is None:
            matched = unit_text[hit.start() : hit.end()].strip()
            evidence = _exact_evidence(matched, raw_text)
        if evidence is None:
            continue
        return FieldExtraction(
            value=True,
            evidence=evidence,
            confidence=0.92,
            status="FOUND",
        )

    return FieldExtraction(
        value=False,
        evidence=_inspected_section_marker(section, raw_text),
        confidence=0.75,
        status="NOT_FOUND",
    )


def scan_late_penalty_rate(raw_text: str, clause: FieldExtraction) -> FieldExtraction:
    """Derive late_penalty_pct_per_week from a FOUND clause scan."""
    if clause.status == "NOT_FOUND":
        return FieldExtraction(
            value=None,
            evidence=None,
            confidence=None,
            status="NOT_FOUND",
        )
    if clause.status != "FOUND" or not clause.evidence:
        return FieldExtraction(
            value=None,
            evidence=None,
            confidence=None,
            status="UNCERTAIN",
        )
    rate = extract_weekly_penalty_pct(clause.evidence)
    if rate is None:
        return FieldExtraction(
            value=None,
            evidence=None,
            confidence=None,
            status="UNCERTAIN",
        )
    evidence = _exact_evidence(clause.evidence, raw_text)
    if evidence is None:
        return FieldExtraction(
            value=None,
            evidence=None,
            confidence=None,
            status="UNCERTAIN",
        )
    return FieldExtraction(
        value=rate,
        evidence=evidence,
        confidence=0.92,
        status="FOUND",
    )
