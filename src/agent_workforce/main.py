"""Entry point: `agent-workforce <issue-number>` takes one board ticket to a green pull request.

Order at boot: read the estate (refuse dark), point crewAI's stores at the volume, install the
two trace exporters, check the laws are present, run, then prove the trace landed by querying
Langfuse and printing the answer in the run log.
"""

from __future__ import annotations

import os
import sys
import uuid

import requests

from agent_workforce import estate as estate_mod
from agent_workforce.estate import EXIT_DARK, Dark


def _langfuse_trace_count(est: estate_mod.Estate, run_id: str) -> int:
    """Ask Langfuse for this run's traces. The number printed in the log is the acceptance receipt."""
    answer = requests.get(
        f"{est.langfuse_base_url.rstrip('/')}/api/public/traces",
        params={"sessionId": run_id, "limit": 1},
        auth=(est.langfuse_public_key, est.langfuse_secret_key),
        timeout=30,
    )
    answer.raise_for_status()
    return int(answer.json().get("meta", {}).get("totalItems", 0))


# The lanes the workforce takes work from. These are the labels the board actually carries; a
# label that does not exist on the board matches nothing, which is how the first deployment ran
# for a fortnight without ever picking up a ticket (crew#850 CP0).
DEFAULT_QUEUE_LABELS = (
    "lane:platform",
    "lane:agents",
    "lane:observability",
    "lane:security",
    "lane:process",
    "lane:dr",
)
QUEUE_LABELS = tuple(
    label.strip()
    for label in os.environ.get("AGENT_WORKFORCE_QUEUE_LABELS", ",".join(DEFAULT_QUEUE_LABELS)).split(",")
    if label.strip()
)
CLAIM_MARK = "Optimised:"  # a ticket with a plan comment ending in this line has been taken


def next_ticket(est: estate_mod.Estate, board_repo: str) -> int | None:
    """The queue: the oldest open ticket in any queued lane with no plan comment yet. None when idle.

    GitHub's `labels` filter is an AND, so one call per lane and merge; the board's own creation
    order decides which of them is oldest.
    """
    from agent_workforce.tools.github_client import GitHub

    gh = GitHub(api=est.github_api, token=est.github_token)
    repo = f"{est.repo_owner}/{board_repo}"
    queued: dict[int, dict] = {}
    for label in QUEUE_LABELS:
        for issue in gh.open_issues(repo, label):
            queued.setdefault(int(issue["number"]), issue)
    for _, issue in sorted(queued.items(), key=lambda kv: (kv[1].get("created_at") or "", kv[0])):
        comments = gh.issue_comments(repo, issue["number"])
        if not any(CLAIM_MARK in (c.get("body") or "") for c in comments):
            return int(issue["number"])
    return None


def run(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) > 1 or (argv and not argv[0].isdigit()):
        print(
            "usage: agent-workforce [board issue number]   (no number: take the next queued ticket)",
            file=sys.stderr,
        )
        return 2
    board_repo = os.environ.get("AGENT_WORKFORCE_BOARD_REPO", "crew")

    try:
        est = estate_mod.load()
        if argv:
            issue_number = int(argv[0])
        else:
            queued = next_ticket(est, board_repo)
            if queued is None:
                print(f"idle: no open ticket without a plan comment in {', '.join(QUEUE_LABELS)}")
                return 0
            issue_number = queued
        os.environ.setdefault("CREWAI_STORAGE_DIR", str(est.storage_dir))
        os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")  # the vendor's phone-home, not ours
        run_id = f"agent-workforce-{issue_number}-{uuid.uuid4().hex[:8]}"

        from agent_workforce import knowledge, observability

        knowledge.law_paths(est.laws_dir)
        provider = observability.install(est, run_id)
    except Dark as why:
        print(f"REFUSED: {why}", file=sys.stderr)
        return EXIT_DARK

    from opentelemetry import trace

    from agent_workforce.crew import AgentWorkforce

    tracer = trace.get_tracer("agent_workforce")
    with tracer.start_as_current_span(
        "agent-workforce.run",
        attributes={"langfuse.session.id": run_id, "session.id": run_id, "board.issue": issue_number},
    ):
        result = (
            AgentWorkforce(est).crew().kickoff(inputs={"issue_number": issue_number, "board_repo": board_repo})
        )
    provider.force_flush()
    print(result.raw)

    traces = _langfuse_trace_count(est, run_id)
    print(f"langfuse traces for session {run_id}: {traces}")
    return 0 if traces > 0 else 4


if __name__ == "__main__":
    sys.exit(run())
