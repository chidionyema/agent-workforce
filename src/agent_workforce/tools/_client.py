"""One GitHub client per process, built from the estate at first use."""

from __future__ import annotations

from functools import lru_cache

from agent_workforce.estate import load
from agent_workforce.tools.github_client import GitHub


@lru_cache(maxsize=1)
def github() -> GitHub:
    estate = load()
    return GitHub(api=estate.github_api, token=estate.github_token)


@lru_cache(maxsize=1)
def owner() -> str:
    return load().repo_owner


def full(repo: str) -> str:
    """Accept 'idp' or 'owner/idp'; always return 'owner/idp'."""
    return repo if "/" in repo else f"{owner()}/{repo}"
