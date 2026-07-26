"""Per-provider resolution adapters (fn-139.4/.6).

`resolver_for(provider)` is the dispatch the resolve verb builds on: each
provider module exposes `resolve_destination(config, execute)` and
`resolve_capabilities(config, execute)`. GitHub + GitLab arrive in task .4;
Linear + Jira in task .6 - `resolver_for` on a not-yet-shipped provider raises
KeyError so a caller cannot silently half-resolve.
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

__all__ = ["resolver_for"]

_PROVIDERS = {"github", "gitlab"}  # .6 adds linear + jira


def resolver_for(provider: str) -> ModuleType:
    if provider not in _PROVIDERS:
        raise KeyError(f"no resolver for provider {provider!r}; "
                       f"available: {sorted(_PROVIDERS)}")
    return import_module(f".{provider}", __name__)
