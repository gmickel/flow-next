"""Per-provider resolution adapters (fn-139.4/.6).

`resolver_for(provider)` is the dispatch the resolve verb builds on: each
provider module exposes `resolve_destination(config, execute)` and
`resolve_capabilities(config, execute)`; Linear/Jira additionally expose their
ids-scope resolvers (`resolve_state_ids` / `resolve_status_ids`) and the live
fetchers `--select` validates against. `resolver_for` on an unknown provider
raises KeyError so a caller cannot silently half-resolve.
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType

__all__ = ["resolver_for"]

_PROVIDERS = {"github", "gitlab", "linear", "jira"}


def resolver_for(provider: str) -> ModuleType:
    if provider not in _PROVIDERS:
        raise KeyError(f"no resolver for provider {provider!r}; "
                       f"available: {sorted(_PROVIDERS)}")
    return import_module(f".{provider}", __name__)
