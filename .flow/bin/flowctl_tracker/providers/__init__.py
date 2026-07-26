"""Per-provider adapters (GitHub, GitLab, Linear, Jira).

Empty by design in spec A task .1. The injected executor and the typed
Request/Response layer arrive in task .2; the adapters themselves in .4 and .6.
This module exists now so the package shape - and its importability under both
the test harness and the real launcher - is proven before anything depends on it.
"""

__all__: list[str] = []
