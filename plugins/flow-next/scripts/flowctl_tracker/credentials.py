"""Provider credential resolution (fn-139.2).

flow-next implements **no keyring**. "Secure store" means whatever the host OS
provides and the user has already exported into their environment - an earlier
draft of this spec had a generic `env -> Keychain -> CLI config` ladder, which
promised a cross-platform secret store that does not exist here.

Resolution is per provider and by exact name, never a generic ladder.
"""

from __future__ import annotations

import os
from typing import Callable, Optional


class Credential:
    """A resolved secret plus how to attach it. Never logged, never persisted."""

    __slots__ = ("_apply",)

    def __init__(self, apply: Callable[[dict[str, str]], None]) -> None:
        self._apply = apply

    def attach(self, headers: dict[str, str]) -> None:
        self._apply(headers)

    def __repr__(self) -> str:  # pragma: no cover - defensive
        return "<Credential redacted>"


def _glab_config_token() -> Optional[str]:
    """Read glab's stored token. Not a keyring - glab's own config file."""
    import re

    for candidate in (
        os.path.expanduser("~/.config/glab-cli/config.yml"),
        os.path.expanduser("~/Library/Application Support/glab-cli/config.yml"),
    ):
        try:
            with open(candidate, encoding="utf-8") as fh:
                m = re.search(r"^\s+token:\s*(\S+)", fh.read(), re.M)
            if m:
                return m.group(1)
        except OSError:
            continue
    return None


def _basic(user: str, token: str) -> str:
    import base64

    return "Basic " + base64.b64encode(f"{user}:{token}".encode()).decode()


def resolve(provider: str, *, auth_scheme: Optional[str] = None) -> Optional[Credential]:
    """Return a Credential, or None when the transport authenticates itself.

    GitHub and GitLab ordinarily go through their CLI, which carries its own
    auth - so None there is correct, not a failure.
    """
    if provider == "github":
        tok = os.environ.get("GH_TOKEN")
        return Credential(lambda h: h.__setitem__("Authorization", f"Bearer {tok}")) if tok else None

    if provider == "gitlab":
        # Ordinary calls go through `glab`, which authenticates itself - but the
        # upload route MUST use HTTP, and returning None there would send it
        # unauthenticated. So fall back to glab's own stored token.
        tok = os.environ.get("GITLAB_TOKEN") or _glab_config_token()
        return Credential(lambda h: h.__setitem__("PRIVATE-TOKEN", tok)) if tok else None

    if provider == "linear":
        key = os.environ.get("LINEAR_API_KEY")
        return Credential(lambda h: h.__setitem__("Authorization", key)) if key else None

    if provider == "jira":
        # Selected by the PERSISTED authScheme rather than re-racing both sets
        # every run: a site is Cloud or Data Center, and that does not change
        # between invocations. Racing them would also make "which credential
        # failed" unanswerable when both are present.
        if auth_scheme == "bearer-pat":
            pat = os.environ.get("JIRA_PAT")
            return Credential(lambda h: h.__setitem__("Authorization", f"Bearer {pat}")) if pat else None
        email, tok = os.environ.get("JIRA_EMAIL"), os.environ.get("JIRA_API_TOKEN")
        if email and tok:
            return Credential(lambda h: h.__setitem__("Authorization", _basic(email, tok)))
        return None

    return None


def redact(text: str) -> str:
    """Strip any resolvable secret from a string bound for a log or error."""
    out = text
    for name in ("GH_TOKEN", "GITLAB_TOKEN", "LINEAR_API_KEY", "JIRA_API_TOKEN", "JIRA_PAT"):
        val = os.environ.get(name)
        if val and len(val) >= 8:
            out = out.replace(val, f"<{name} redacted>")
    return out
