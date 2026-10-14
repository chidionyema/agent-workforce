"""The estate's shared memory, as two tools: look up what is already known, and keep a finding.

Both are no-ops that say so when the workload has not named the memory gateway, and neither can
fail a task: an outage comes back as a sentence the agent can read and carry on past.
"""

from __future__ import annotations

import json

from crewai.tools import tool

from agent_workforce import estate_memory

UNAVAILABLE = "estate memory is not available in this run; carry on without it."


@tool("recall")
def recall(query: str, limit: int = 8) -> str:
    """Search the estate's shared memory (earlier crew runs, Otto, the operator's sessions) by meaning."""
    found = estate_memory.recall(query, limit)
    if found is None:
        return UNAVAILABLE
    return found if isinstance(found, str) else json.dumps(found, indent=1)


@tool("remember")
def remember(content: str, subject: str = "") -> str:
    """Keep one durable finding in the estate's shared memory: a fact, a ruling or a lesson, in one sentence."""
    if estate_memory.remember(content, subject=subject):
        return "remembered."
    return UNAVAILABLE
