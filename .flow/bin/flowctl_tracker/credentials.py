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


def _glab_config_token(host: Optional[str] = None) -> Optional[str]:
    """Read glab's stored token FOR A SPECIFIC HOST. Not a keyring - glab's config.

    Host scoping is the point: taking the first token in the file would send a
    self-managed instance's token to gitlab.com (or the reverse) whenever a user
    has more than one authenticated host. Fails closed when no stanza matches.
    """
    import re

    want = (host or "gitlab.com").lower()
    for candidate in (
        os.path.expanduser("~/.config/glab-cli/config.yml"),
        os.path.expanduser("~/Library/Application Support/glab-cli/config.yml"),
    ):
        try:
            with open(candidate, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        # hosts:\n    <host>:\n        token: <value>
        m = re.search(
            rf"^\s+{re.escape(want)}:\s*$(.*?)(?=^\s{{0,8}}\S+:\s*$|\Z)",
            text, re.M | re.S,
        )
        if m:
            tok = re.search(r"^\s+token:\s*(\S+)", m.group(1), re.M)
            if tok:
                return tok.group(1)
    return None


def _basic(user: str, token: str) -> str:
    import base64

    return "Basic " + base64.b64encode(f"{user}:{token}".encode()).decode()


def resolve(provider: str, *, auth_scheme: Optional[str] = None,
            host: Optional[str] = None) -> Optional[Credential]:
    """Return a Credential, or None when the transport authenticates itself.

    GitHub and GitLab ordinarily go through their CLI, which carries its own
    auth - so None there is correct, not a failure.
    """
    if provider == "github":
        tok = _remember(os.environ.get("GH_TOKEN"))
        return Credential(lambda h: h.__setitem__("Authorization", f"Bearer {tok}")) if tok else None

    if provider == "gitlab":
        # Ordinary calls go through `glab`, which authenticates itself - but the
        # upload route MUST use HTTP, and returning None there would send it
        # unauthenticated. So fall back to glab's own stored token.
        tok = _remember(os.environ.get("GITLAB_TOKEN") or _glab_config_token(host))
        return Credential(lambda h: h.__setitem__("PRIVATE-TOKEN", tok)) if tok else None

    if provider == "linear":
        key = _remember(os.environ.get("LINEAR_API_KEY"))
        return Credential(lambda h: h.__setitem__("Authorization", key)) if key else None

    if provider == "jira":
        # Selected by the PERSISTED authScheme rather than re-racing both sets
        # every run: a site is Cloud or Data Center, and that does not change
        # between invocations. Racing them would also make "which credential
        # failed" unanswerable when both are present.
        if auth_scheme == "bearer-pat":
            pat = _remember(os.environ.get("JIRA_PAT"))
            return Credential(lambda h: h.__setitem__("Authorization", f"Bearer {pat}")) if pat else None
        email, tok = os.environ.get("JIRA_EMAIL"), _remember(os.environ.get("JIRA_API_TOKEN"))
        if email and tok:
            return Credential(lambda h: h.__setitem__("Authorization", _basic(email, tok)))
        return None

    return None


#: Every secret this process has actually resolved, including ones that never
#: appear in the environment. Scanning env vars alone missed the glab-config
#: token used by the mandatory GitLab HTTP upload route, so a provider echoing
#: it back would have leaked it.
_SEEN: set[str] = set()


#: Refuse, rather than exempt-from-redaction, a credential too short to redact
#: safely. A round-7 length floor inside `redact()` was the wrong end of the
#: problem: it let a 3-character token attach to a live request while being
#: deliberately excluded from scrubbing, which breaks R6 outright. Rejecting at
#: resolution keeps `redact()` floorless AND keeps a 1-2 char value from
#: shredding every message it happens to appear inside. No provider here issues
#: a credential this short, so nothing legitimate is refused.
MIN_CREDENTIAL_LEN = 4


class ShortCredential(ValueError):
    """Resolved a credential too short to be real. Never carries the value."""


def _remember(value: Optional[str]) -> Optional[str]:
    if value and len(value) < MIN_CREDENTIAL_LEN:
        raise ShortCredential(
            f"resolved credential is shorter than {MIN_CREDENTIAL_LEN} characters; "
            "refusing to use it (a value this short cannot be redacted from logs)"
        )
    if value:
        _SEEN.add(value)
    return value


def redact(text: str) -> str:
    """Strip every known secret from a string bound for a log, error or receipt."""
    out = text
    for name in ("GH_TOKEN", "GITLAB_TOKEN", "LINEAR_API_KEY", "JIRA_API_TOKEN", "JIRA_PAT"):
        val = os.environ.get(name)
        # Same rule as `_remember`: a value this short is never a usable
        # credential (resolution refuses it), and adding it here would let a
        # stray `JIRA_PAT=p` rewrite every message containing the letter p.
        if val and len(val) >= MIN_CREDENTIAL_LEN:
            _SEEN.add(val)
    # NO length floor. Everything in `_SEEN` was accepted by `_remember`, which
    # refuses anything under MIN_CREDENTIAL_LEN - so "too short to redact" is
    # handled by rejecting the credential, never by exempting it here.
    for secret in sorted(_SEEN, key=len, reverse=True):
        if secret:
            out = out.replace(secret, "<redacted>")
    return out
