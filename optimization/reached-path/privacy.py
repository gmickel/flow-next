"""Privacy scrubs for reached-path fixtures and run artifacts (fn-130)."""

from __future__ import annotations

import re
from typing import Any

# Emails, bearer-ish tokens, private absolute homes, obvious secrets.
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_TOKEN_RE = re.compile(
    r"(?i)\b(sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{10,}|Bearer\s+[A-Za-z0-9._\-]+)\b"
)
_HOME_RE = re.compile(r"(?i)(/Users/[^/\s]+|/home/[^/\s]+|C:\\Users\\[^\\\s]+)")
_SENTINEL_RE = re.compile(r"SENTINEL-[0-9a-f]{8,}")


def scrub_text(text: str) -> str:
    """Redact emails, tokens, home prefixes, and sentinel values."""
    if not text:
        return text
    out = _EMAIL_RE.sub("[REDACTED-EMAIL]", text)
    out = _TOKEN_RE.sub("[REDACTED-TOKEN]", out)
    out = _HOME_RE.sub("[REDACTED-HOME]", out)
    out = _SENTINEL_RE.sub("[REDACTED-SENTINEL]", out)
    return out


def scrub_obj(obj: Any) -> Any:
    """Deep-scrub strings in JSON-serializable structures."""
    if isinstance(obj, str):
        return scrub_text(obj)
    if isinstance(obj, list):
        return [scrub_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {k: scrub_obj(v) for k, v in obj.items()}
    return obj


def assert_no_answer_key_leak(subject_visible: str, answer_key: str) -> None:
    """Subject fixtures must not embed answer-key conclusions verbatim."""
    key = (answer_key or "").strip()
    if not key:
        return
    if key in (subject_visible or ""):
        raise ValueError("answer-key conclusion leaked into subject-visible fixture text")
