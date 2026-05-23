"""
Lightweight PII scrubber using compiled regex patterns.

Applied to user-supplied text before it is passed to any LLM or tracer,
so names, emails, and phone numbers are replaced with typed placeholders
rather than sent to external services.

Patterns covered:
  - Email addresses
  - US/international phone numbers
  - US Social Security Numbers (SSN)
  - Payment card numbers (16-digit)

Limitations: regex-only, no NLP entity detection.  For a production system
use presidio-analyzer; this covers the most common accidental PII leaks.
"""

import re
from typing import Optional

# Each tuple is (compiled pattern, replacement label).
_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Email  —  user@domain.tld
    (
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
        "[EMAIL]",
    ),
    # US phone — (123) 456-7890 / +1-123-456-7890 / 123.456.7890 etc.
    (
        re.compile(
            r"\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"
        ),
        "[PHONE]",
    ),
    # SSN — 123-45-6789
    (
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "[SSN]",
    ),
    # Payment card — 16 digits with optional separators
    (
        re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
        "[CARD]",
    ),
]


def scrub(text: Optional[str]) -> str:
    """Replace detected PII spans with typed placeholders. Returns '' for None."""
    if not text:
        return text or ""
    for pattern, label in _PATTERNS:
        text = pattern.sub(label, text)
    return text


def scrub_list(items: Optional[list[str]]) -> Optional[list[str]]:
    """Scrub each string in a list; preserves None input."""
    if items is None:
        return None
    return [scrub(item) for item in items]
