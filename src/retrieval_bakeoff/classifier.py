from __future__ import annotations

import re


_ENUMERATION = re.compile(r"\b(across|all|list)\b", re.IGNORECASE)
_CHAINED = re.compile(r"\b(pair|connect|both)\b", re.IGNORECASE)
_SUBJECT_COUNT = re.compile(
    r"\b(?:three|four|five|six|seven|eight|nine|ten|eleven|twelve|\d+)"
    r"\s+(?:subject (?:areas|threads)|threads|domains)\b",
    re.IGNORECASE,
)


def classify_query(text: str, domain_labels: tuple[str, ...]) -> str:
    lowered = text.casefold()
    domain_count = sum(label.casefold() in lowered for label in domain_labels)
    if _ENUMERATION.search(text) and (
        domain_count >= 3 or _SUBJECT_COUNT.search(text)
    ):
        return "enumeration"
    if _CHAINED.search(text) or domain_count >= 2:
        return "chained"
    return "lookup"
